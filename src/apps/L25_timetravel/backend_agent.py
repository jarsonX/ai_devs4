# Bounded backend agent that combines semantic extraction with guarded Hub tools.

from __future__ import annotations

from math import isclose

from src.apps.L25_timetravel.hub_client import TimetravelHubClient
from src.apps.L25_timetravel.llm_gateway import L25ModelGateway
from src.apps.L25_timetravel.machine_spec import calculate_stabilization
from src.apps.L25_timetravel.models import MachineSnapshot, TravelLeg


# Prepare backend-only fields for one supervisor command and no activation.
class BackendAgent:
    # Store only the narrow Hub and model boundaries assigned to this role.
    def __init__(self, hub: TimetravelHubClient, model: L25ModelGateway) -> None:
        self.hub = hub
        self.model = model

    # Configure one leg and return the authoritative stabilized snapshot.
    def prepare_leg(self, leg: TravelLeg) -> MachineSnapshot:
        state = self.hub.get_config()
        if state.mode != "standby":
            raise RuntimeError("Backend Agent requires standby before configuration.")
        desired: list[tuple[str, int | float]] = [
            ("year", leg.target.year),
            ("month", leg.target.month),
            ("day", leg.target.day),
            ("syncRatio", leg.sync_ratio),
        ]
        for param, value in desired:
            current = getattr(state, param)
            matches = (
                isclose(float(current), float(value), abs_tol=0.0001)
                if current is not None and param == "syncRatio"
                else current == value
            )
            if not matches:
                state = self.hub.configure(param, value)
        state = self.hub.get_config()
        if self.matches_leg(state, leg):
            return state
        hint = state.needConfig
        if not hint:
            raise RuntimeError("Hub returned no stabilization challenge.")
        expression = self.model.extract_stabilization(hint)
        stabilization = calculate_stabilization(
            expression.left, expression.operator, expression.right
        )
        if state.stabilization != stabilization:
            state = self.hub.configure("stabilization", stabilization)
        state = self.hub.get_config()
        if not self.matches_leg(state, leg):
            raise RuntimeError("Backend configuration did not converge to the leg goal.")
        return state

    # Validate every backend-owned activation prerequisite for one leg.
    @staticmethod
    def matches_leg(state: MachineSnapshot, leg: TravelLeg) -> bool:
        return (
            state.target() == leg.target
            and state.syncRatio is not None
            and isclose(state.syncRatio, leg.sync_ratio, abs_tol=0.0001)
            and state.stabilization is not None
            and state.condition == "stable"
            and state.mode == "standby"
        )
