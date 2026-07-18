# Complete in-process simulation of the three-leg L25 workflow.

from __future__ import annotations

import tempfile
from pathlib import Path

from src.apps.L25_timetravel.backend_agent import BackendAgent
from src.apps.L25_timetravel.config import AppPaths, RuntimeConfig
from src.apps.L25_timetravel.coordination import CoordinationStore
from src.apps.L25_timetravel.frontend_agent import FrontendAgent
from src.apps.L25_timetravel.machine_spec import load_pwr_table, required_internal_mode
from src.apps.L25_timetravel.models import (
    FrontendAction,
    FrontendDecision,
    FrontendObservation,
    MachineSnapshot,
    StabilizationExpression,
    TravelLeg,
)
from src.apps.L25_timetravel.supervisor import TimetravelSupervisor


# Hold the fake machine's single shared state across Hub and browser boundaries.
class OfflineMachine:
    # Start from the observed safe pre-task state with one charged cell.
    def __init__(self) -> None:
        self.state = MachineSnapshot(
            currentDate="2026-07-18",
            condition="unstable",
            fluxDensity=0,
            batteryStatus="1/3",
            PTA=False,
            PTB=False,
            PWR=0,
            mode="standby",
            internalMode=1,
            needConfig="Ustaw stabilizację na wynik działania 19 razy 7.",
        )
        self.activations = 0

    # Return a detached snapshot like a network or DOM read would.
    def snapshot(self) -> MachineSnapshot:
        return self.state.model_copy(deep=True)


# Mimic only the typed Hub tools available to BackendAgent and Supervisor.
class OfflineHub:
    # Store shared state and a logical request counter for guard reporting.
    def __init__(self, machine: OfflineMachine) -> None:
        self.machine = machine
        self.requests = 0

    # Return the current authoritative fake backend state.
    def get_config(self) -> MachineSnapshot:
        self.requests += 1
        return self.machine.snapshot()

    # Apply one backend parameter and invalidate stale stabilization when needed.
    def configure(self, param: str, value: int | float) -> MachineSnapshot:
        self.requests += 1
        updates = {param: value}
        if param == "stabilization":
            updates.update(condition="stable")
        else:
            updates.update(stabilization=None, condition="unstable", fluxDensity=0)
        self.machine.state = self.machine.state.model_copy(update=updates)
        return self.machine.snapshot()

    # Return the number of simulated logical Hub operations.
    def request_count(self) -> int:
        return self.requests


# Provide deterministic semantic extraction in a network-free full simulation.
class OfflineBackendModel:
    # Return the expression embedded in OfflineMachine's fixed challenge.
    def extract_stabilization(self, hint: str) -> StabilizationExpression:
        if "19" not in hint or "7" not in hint:
            raise ValueError("Offline stabilization fixture changed unexpectedly.")
        return StabilizationExpression(left=19, operator="*", right=7)


# Choose the same bounded actions expected from the real Frontend Agent model.
class OfflineFrontendModel:
    # Select one corrective control operation or report readiness.
    def choose_frontend_action(
        self,
        leg: TravelLeg,
        observation: FrontendObservation,
        last_error: str | None = None,
    ) -> FrontendDecision:
        machine = observation.machine
        if machine.PTA != leg.pta or machine.PTB != leg.ptb:
            return FrontendDecision(
                action=FrontendAction.SET_PORTS,
                pta=leg.pta,
                ptb=leg.ptb,
                reason="Match the assigned protection ports.",
            )
        if machine.PWR != leg.pwr:
            return FrontendDecision(
                action=FrontendAction.SET_POWER,
                pwr=leg.pwr,
                reason="Match the assigned PWR value.",
            )
        if machine.mode != "active":
            return FrontendDecision(
                action=FrontendAction.SET_MODE,
                mode="active",
                reason="Start automatic mode rotation.",
            )
        return FrontendDecision(
            action=FrontendAction.READY,
            reason="All simulated readiness signals match.",
        )


# Mimic the approved browser tools while sharing state with OfflineHub.
class OfflineBrowser:
    # Store shared state and every consumed lease for duplicate detection.
    def __init__(self, machine: OfflineMachine) -> None:
        self.machine = machine
        self.used_leases: set[str] = set()

    # Convert fake machine state into the frontend-only observation contract.
    def snapshot(self) -> FrontendObservation:
        state = self.machine.snapshot()
        ready = (
            state.mode == "active"
            and state.condition == "stable"
            and state.fluxDensity == 100
        )
        same_date = (
            state.target() is not None
            and state.target().isoformat() == state.currentDate
        )
        return FrontendObservation(
            machine=state,
            orb_powered=ready,
            orb_danger=not ready,
            activation_ready=ready,
            same_date_warning=same_date,
        )

    # Apply the two simulated PT switches.
    def set_ports(self, pta: bool, ptb: bool) -> FrontendObservation:
        self.machine.state = self.machine.state.model_copy(
            update={"PTA": pta, "PTB": ptb}
        )
        return self.snapshot()

    # Apply the simulated protection power.
    def set_power(self, value: int) -> FrontendObservation:
        self.machine.state = self.machine.state.model_copy(update={"PWR": value})
        return self.snapshot()

    # Enter standby or lock the automatic mode to the target's required test value.
    def set_mode(self, mode: str) -> FrontendObservation:
        updates: dict[str, object] = {"mode": mode, "fluxDensity": 0}
        if mode == "active":
            year = self.machine.state.year
            if year is None:
                raise RuntimeError("Offline machine cannot activate without a year.")
            updates.update(
                internalMode=required_internal_mode(year),
                fluxDensity=100 if self.machine.state.condition == "stable" else 0,
            )
        self.machine.state = self.machine.state.model_copy(update=updates)
        return self.snapshot()

    # Return immediately only when the complete simulated frontend barrier matches.
    def wait_until_ready(self, leg: TravelLeg) -> FrontendObservation:
        observed = self.snapshot()
        state = observed.machine
        if not (
            state.target() == leg.target
            and state.PTA == leg.pta
            and state.PTB == leg.ptb
            and state.PWR == leg.pwr
            and state.mode == "active"
            and state.internalMode == leg.required_internal_mode
            and state.fluxDensity == 100
            and observed.activation_ready
            and not observed.same_date_warning
        ):
            raise RuntimeError("Offline frontend readiness barrier failed.")
        return observed

    # Consume one real SQLite lease and simulate one accepted time-travel response.
    def activate_once(
        self,
        store: CoordinationStore,
        lease_id: str,
        run_id: str,
        state_version: int,
        config_digest: str,
        leg: TravelLeg,
        *,
        evidence_path: Path | None = None,
    ) -> dict[str, object]:
        if lease_id in self.used_leases:
            raise RuntimeError("Offline activation lease was reused.")
        self.wait_until_ready(leg)
        store.consume_activation_lease(
            lease_id, run_id, state_version, config_digest
        )
        self.used_leases.add(lease_id)
        self.machine.activations += 1
        if leg.name == "battery_jump":
            battery = "3/3"
        elif leg.name == "return":
            battery = "2/3"
        else:
            battery = "1/3"
        self.machine.state = self.machine.state.model_copy(
            update={
                "currentDate": leg.target.isoformat(),
                "day": None,
                "month": None,
                "year": None,
                "syncRatio": None,
                "stabilization": None,
                "condition": "unstable",
                "fluxDensity": 0,
                "batteryStatus": battery,
                "mode": "standby",
            }
        )
        payload: dict[str, object] = {"code": 13, "message": "accepted"}
        if leg.tunnel:
            payload["flag"] = "{FLG:" + "offline-simulation}"
        return payload


# Execute the production supervisor against a complete network-free fake machine.
def run_offline_simulation(paths: AppPaths) -> dict[str, object]:
    machine = OfflineMachine()
    hub = OfflineHub(machine)
    browser = OfflineBrowser(machine)
    runtime = RuntimeConfig(
        request_timeout_seconds=2,
        mode_wait_timeout_seconds=2,
        poll_interval_seconds=0.01,
        post_write_settle_seconds=0.01,
    )
    with tempfile.TemporaryDirectory(prefix="l25-offline-") as directory:
        run_dir = Path(directory) / "offline-run"
        run_dir.mkdir()
        store = CoordinationStore(run_dir / "coordination.sqlite3")
        try:
            supervisor = TimetravelSupervisor(
                store,
                hub,
                browser,
                BackendAgent(hub, OfflineBackendModel()),
                FrontendAgent(browser, OfflineFrontendModel(), runtime),
                runtime,
                run_dir,
                load_pwr_table(paths.input_doc),
            )
            result = supervisor.run()
            final_run = store.get_run(supervisor.run_id)
        finally:
            store.close()
    if result["status"] != "solved" or machine.activations != 3:
        raise AssertionError("Offline workflow did not complete exactly three legs.")
    return {
        "status": "passed",
        "network_used": False,
        "activations": machine.activations,
        "flag_found": bool(result.get("flag")),
        "final_phase": final_run["phase"],
        "hub_operations": hub.request_count(),
    }
