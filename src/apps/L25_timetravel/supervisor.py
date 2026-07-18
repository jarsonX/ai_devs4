# Deterministic state machine and activation barrier for L25 timetravel.

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from src.apps.L25_timetravel.backend_agent import BackendAgent
from src.apps.L25_timetravel.browser_tools import (
    ActivationAmbiguousError,
    TimetravelBrowser,
)
from src.apps.L25_timetravel.config import RuntimeConfig
from src.apps.L25_timetravel.coordination import CoordinationStore
from src.apps.L25_timetravel.frontend_agent import FrontendAgent
from src.apps.L25_timetravel.hub_client import TimetravelHubClient
from src.apps.L25_timetravel.machine_spec import build_travel_plan
from src.apps.L25_timetravel.models import (
    AgentRole,
    FrontendObservation,
    MachineSnapshot,
    Phase,
    TravelLeg,
)


PREPARE_PHASES = [Phase.PREPARE_2238, Phase.PREPARE_RETURN, Phase.PREPARE_2024_TUNNEL]
WAIT_PHASES = [Phase.WAIT_MODE_3, Phase.WAIT_MODE_2_RETURN, Phase.WAIT_MODE_2_TUNNEL]
ACTION_PHASES = [Phase.JUMP_2238, Phase.JUMP_TO_PRESENT, Phase.OPEN_TUNNEL]
VERIFY_PHASES = [
    Phase.VERIFY_BATTERY_REPLACEMENT,
    Phase.VERIFY_PRESENT,
    Phase.VERIFY_FLAG,
]
FLAG_PATTERN = re.compile(r"\{FLG:[^{}]+\}")


# Write raw course runtime data only inside the approved ignored run directory.
def write_runtime_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# Build a stable digest for the exact cross-checked activation configuration.
def configuration_digest(leg: TravelLeg, backend: MachineSnapshot) -> str:
    payload = {
        "leg": leg.model_dump(mode="json"),
        "stabilization": backend.stabilization,
        "condition": backend.condition,
        "internalMode": backend.internalMode,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# Find a course flag anywhere in a raw activation response without assuming shape.
def extract_flag(payload: Any) -> str | None:
    if isinstance(payload, str):
        match = FLAG_PATTERN.search(payload)
        return match.group(0) if match else None
    if isinstance(payload, dict):
        for value in payload.values():
            found = extract_flag(value)
            if found:
                return found
    if isinstance(payload, list):
        for value in payload:
            found = extract_flag(value)
            if found:
                return found
    return None


# Coordinate two narrow agents while retaining all transition and activation authority.
class TimetravelSupervisor:
    # Store collaborators and run-local durable paths without loading secrets.
    def __init__(
        self,
        store: CoordinationStore,
        hub: TimetravelHubClient,
        browser: TimetravelBrowser,
        backend_agent: BackendAgent,
        frontend_agent: FrontendAgent,
        runtime: RuntimeConfig,
        run_dir: Path,
        pwr_table: dict[int, int],
    ) -> None:
        self.store = store
        self.hub = hub
        self.browser = browser
        self.backend_agent = backend_agent
        self.frontend_agent = frontend_agent
        self.runtime = runtime
        self.run_dir = run_dir
        self.pwr_table = pwr_table
        self.run_id = store.create_run(run_dir.name)
        self.state_version = 1

    # Execute exactly three planned activations and stop on the first ambiguity.
    def run(self) -> dict[str, Any]:
        try:
            initial = self.hub.get_config()
            frozen = date.fromisoformat(initial.currentDate)
            plan = build_travel_plan(frozen, self.pwr_table)
            self.state_version = self.store.transition_run(
                self.run_id,
                self.state_version,
                PREPARE_PHASES[0],
                frozen_current_date=frozen.isoformat(),
                active_leg=0,
            )
            activations: list[dict[str, Any]] = []
            flag: str | None = None
            for index, leg in enumerate(plan):
                payload = self._run_leg(index, leg)
                activations.append(payload)
                flag = extract_flag(payload) or flag
                self._verify_arrival(index, leg, frozen, flag)
                if index < len(plan) - 1:
                    self.state_version = self.store.transition_run(
                        self.run_id,
                        self.state_version,
                        PREPARE_PHASES[index + 1],
                        active_leg=index + 1,
                    )
            if not flag:
                raise RuntimeError("Final activation returned no course flag.")
            self.state_version = self.store.transition_run(
                self.run_id,
                self.state_version,
                Phase.COMPLETED,
                status="completed",
                flag_found=True,
            )
            return {
                "status": "solved",
                "flag": flag,
                "run_id": self.run_id,
                "activations": len(activations),
                "hub_requests": self.hub.request_count(),
            }
        except ActivationAmbiguousError as error:
            self._mark_terminal(Phase.BLOCKED, "blocked", error)
            raise
        except Exception as error:
            self._mark_terminal(Phase.FAILED, "failed", error)
            raise

    # Prepare, cross-check, lease, and activate one travel leg exactly once.
    def _run_leg(self, index: int, leg: TravelLeg) -> dict[str, Any]:
        frontend = self.browser.snapshot()
        if frontend.machine.mode != "standby":
            self.browser.set_mode("standby")
        backend_prepared = self.backend_agent.prepare_leg(leg)
        self.store.append_observation(
            self.run_id,
            AgentRole.BACKEND,
            "prepared",
            self.state_version,
            backend_prepared.model_dump(mode="json"),
        )
        frontend_prepared = self.frontend_agent.prepare_leg(leg)
        self.store.append_observation(
            self.run_id,
            AgentRole.FRONTEND,
            "prepared",
            self.state_version,
            frontend_prepared.model_dump(mode="json"),
        )
        self.state_version = self.store.transition_run(
            self.run_id, self.state_version, WAIT_PHASES[index]
        )
        backend_ready, frontend_ready = self._wait_for_cross_checked_readiness(leg)
        self.store.append_observation(
            self.run_id,
            AgentRole.BACKEND,
            "activation_ready",
            self.state_version,
            backend_ready.model_dump(mode="json"),
        )
        self.store.append_observation(
            self.run_id,
            AgentRole.FRONTEND,
            "activation_ready",
            self.state_version,
            frontend_ready.model_dump(mode="json"),
        )
        self.state_version = self.store.transition_run(
            self.run_id, self.state_version, ACTION_PHASES[index]
        )
        digest = configuration_digest(leg, backend_ready)
        lease_id = self.store.issue_activation_lease(
            self.run_id,
            self.state_version,
            digest,
            datetime.now(UTC) + timedelta(seconds=self.runtime.activation_lease_seconds),
        )
        evidence_path = self.run_dir / "screenshots" / f"activation_{index + 1}.png"
        payload = self.browser.activate_once(
            self.store,
            lease_id,
            self.run_id,
            self.state_version,
            digest,
            leg,
            evidence_path=evidence_path,
        )
        write_runtime_json(
            self.run_dir / "responses" / f"activation_{index + 1}.json", payload
        )
        self.store.append_event(
            self.run_id,
            AgentRole.SUPERVISOR,
            "activation_completed",
            {"leg": leg.name, "code": payload.get("code")},
        )
        self.state_version = self.store.transition_run(
            self.run_id, self.state_version, VERIFY_PHASES[index]
        )
        return payload

    # Require fresh Hub and DOM views to agree in the same rotating mode window.
    def _wait_for_cross_checked_readiness(
        self, leg: TravelLeg
    ) -> tuple[MachineSnapshot, FrontendObservation]:
        deadline = time.monotonic() + self.runtime.mode_wait_timeout_seconds
        while time.monotonic() < deadline:
            frontend = self.browser.snapshot()
            if self._frontend_matches(frontend, leg):
                backend = self.hub.get_config()
                if self._backend_matches_active(backend, leg):
                    return backend, frontend
            time.sleep(self.runtime.poll_interval_seconds)
        raise RuntimeError("Supervisor readiness barrier timed out.")

    # Check backend-owned and shared prerequisites at the activation barrier.
    @staticmethod
    def _backend_matches_active(state: MachineSnapshot, leg: TravelLeg) -> bool:
        return (
            state.target() == leg.target
            and state.PTA == leg.pta
            and state.PTB == leg.ptb
            and state.PWR == leg.pwr
            and state.mode == "active"
            and state.internalMode == leg.required_internal_mode
            and state.fluxDensity == 100
            and state.condition == "stable"
            and state.stabilization is not None
        )

    # Check frontend-owned and shared prerequisites at the activation barrier.
    @staticmethod
    def _frontend_matches(state: FrontendObservation, leg: TravelLeg) -> bool:
        machine = state.machine
        return (
            machine.target() == leg.target
            and machine.PTA == leg.pta
            and machine.PTB == leg.ptb
            and machine.PWR == leg.pwr
            and machine.mode == "active"
            and machine.internalMode == leg.required_internal_mode
            and machine.fluxDensity == 100
            and machine.condition == "stable"
            and state.activation_ready
            and not state.same_date_warning
        )

    # Reconcile server state after a confirmed response and enforce battery milestones.
    def _verify_arrival(
        self,
        index: int,
        leg: TravelLeg,
        frozen: date,
        flag: str | None,
    ) -> None:
        if index == 2:
            if not flag:
                raise RuntimeError("Tunnel activation was accepted without a flag.")
            return
        expected_date = leg.target.isoformat() if index == 0 else frozen.isoformat()
        deadline = time.monotonic() + self.runtime.request_timeout_seconds
        last: MachineSnapshot | None = None
        while time.monotonic() < deadline:
            last = self.hub.get_config()
            charged, total = last.battery_cells()
            battery_ok = charged == total == 3 if index == 0 else charged >= 2
            if last.currentDate == expected_date and battery_ok:
                return
            time.sleep(self.runtime.poll_interval_seconds)
        detail = last.model_dump(mode="json") if last is not None else None
        raise RuntimeError(f"Arrival reconciliation failed: {detail}")

    # Preserve terminal state without overwriting an earlier transition error.
    def _mark_terminal(self, phase: Phase, status: str, error: Exception) -> None:
        try:
            self.state_version = self.store.transition_run(
                self.run_id,
                self.state_version,
                phase,
                status=status,
                last_error=f"{type(error).__name__}: {error}",
            )
        except Exception:
            pass
