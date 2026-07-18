# Bounded frontend agent that turns model choices into validated browser tools.

from __future__ import annotations

from src.apps.L25_timetravel.browser_tools import TimetravelBrowser
from src.apps.L25_timetravel.config import RuntimeConfig
from src.apps.L25_timetravel.llm_gateway import L25ModelGateway
from src.apps.L25_timetravel.models import FrontendAction, FrontendObservation, TravelLeg


# Prepare browser-owned controls while denying activation to the model loop.
class FrontendAgent:
    # Store the narrow browser, model, and step guard assigned to this role.
    def __init__(
        self,
        browser: TimetravelBrowser,
        model: L25ModelGateway,
        runtime: RuntimeConfig,
    ) -> None:
        self.browser = browser
        self.model = model
        self.runtime = runtime

    # Execute validated model-proposed actions until automatic readiness can be polled.
    def prepare_leg(self, leg: TravelLeg) -> FrontendObservation:
        observation = self.browser.snapshot()
        last_error: str | None = None
        for _ in range(self.runtime.max_tool_steps_per_agent):
            decision = self.model.choose_frontend_action(leg, observation, last_error)
            last_error = None
            if decision.action == FrontendAction.SET_PORTS:
                if decision.pta != leg.pta or decision.ptb != leg.ptb:
                    last_error = "SET_PORTS must exactly match the assigned leg."
                    continue
                observation = self.browser.set_ports(leg.pta, leg.ptb)
            elif decision.action == FrontendAction.SET_POWER:
                if decision.pwr != leg.pwr:
                    last_error = "SET_POWER must exactly match the assigned leg."
                    continue
                observation = self.browser.set_power(leg.pwr)
            elif decision.action == FrontendAction.SET_MODE:
                if decision.mode != "active":
                    last_error = "The preparation command permits only active mode."
                    continue
                observation = self.browser.set_mode("active")
            elif decision.action in {FrontendAction.INSPECT, FrontendAction.READY}:
                if observation.machine.mode != "active":
                    last_error = "INSPECT or READY is premature while mode is standby."
                    continue
                return self.browser.wait_until_ready(leg)
            elif decision.action == FrontendAction.BLOCKED:
                raise RuntimeError(f"Frontend Agent blocked: {decision.reason}")
            else:
                last_error = f"Unsupported action {decision.action.value}."
        raise RuntimeError("Frontend Agent reached its tool-step guard.")
