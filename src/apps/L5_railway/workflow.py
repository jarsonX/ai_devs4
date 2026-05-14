# Build and execute the deterministic railway route activation workflow.

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from src.apps.L5_railway.help_contract import HelpContract
from src.apps.L5_railway.railway_client import RailwayApiClient, RailwayApiResponse


TARGET_ROUTE = "X-01"
TARGET_STATUS = "RTOPEN"
FLAG_PATTERN = re.compile(r"\{FLG:[^}]+\}")


# Store one planned railway API action for the activation workflow.
@dataclass(frozen=True)
class PlannedAction:
    action: str
    fields: dict[str, str]


# Store one executed workflow step together with the API response.
@dataclass(frozen=True)
class WorkflowStepResult:
    action: str
    request_fields: dict[str, Any]
    response: RailwayApiResponse


# Store the final outcome of one route activation workflow run.
@dataclass(frozen=True)
class RouteActivationResult:
    route: str
    target_status: str
    success: bool
    completion_flag: str | None
    terminal_error: str | None
    steps: tuple[WorkflowStepResult, ...]


# Build the deterministic action sequence for opening route X-01.
def build_activation_plan(
    contract: HelpContract,
    route: str = TARGET_ROUTE,
    target_status: str = TARGET_STATUS,
) -> tuple[PlannedAction, ...]:
    validate_workflow_inputs(contract, route, target_status)

    return (
        PlannedAction(action="reconfigure", fields={"route": route}),
        PlannedAction(action="getstatus", fields={"route": route}),
        PlannedAction(action="setstatus", fields={"route": route, "value": target_status}),
        PlannedAction(action="save", fields={"route": route}),
    )


# Execute the deterministic activation workflow and stop on success or terminal error.
def activate_route(
    client: RailwayApiClient,
    contract: HelpContract,
    route: str = TARGET_ROUTE,
    target_status: str = TARGET_STATUS,
) -> RouteActivationResult:
    plan = build_activation_plan(contract, route=route, target_status=target_status)
    step_results: list[WorkflowStepResult] = []

    for planned_action in plan:
        response = client.request_action(planned_action.action, **planned_action.fields)
        step_result = WorkflowStepResult(
            action=planned_action.action,
            request_fields=dict(planned_action.fields),
            response=response,
        )
        step_results.append(step_result)

        completion_flag = extract_completion_flag(response.body)
        if completion_flag is not None:
            return RouteActivationResult(
                route=route,
                target_status=target_status,
                success=True,
                completion_flag=completion_flag,
                terminal_error=None,
                steps=tuple(step_results),
            )

        terminal_error = describe_terminal_error(response)
        if terminal_error is not None:
            return RouteActivationResult(
                route=route,
                target_status=target_status,
                success=False,
                completion_flag=None,
                terminal_error=terminal_error,
                steps=tuple(step_results),
            )

    return RouteActivationResult(
        route=route,
        target_status=target_status,
        success=False,
        completion_flag=None,
        terminal_error="Workflow finished without a completion flag.",
        steps=tuple(step_results),
    )


# Validate the planned route and status against the saved help contract.
def validate_workflow_inputs(
    contract: HelpContract,
    route: str,
    target_status: str,
) -> None:
    if not route.strip():
        raise ValueError("route must be a non-empty string.")

    if not route_matches_contract(route, contract.route_format):
        raise ValueError(
            f"Route '{route}' does not match the documented format '{contract.route_format}'."
        )

    setstatus_action = contract.actions_by_name["setstatus"]
    if target_status not in setstatus_action.allowed_values:
        raise ValueError(
            f"Target status '{target_status}' is not allowed by the saved help contract."
        )

    for required_action in ("reconfigure", "getstatus", "setstatus", "save"):
        if required_action not in contract.actions_by_name:
            raise ValueError(f"Saved help contract is missing required action '{required_action}'.")


# Match one route against the regex-like format documented by the help contract.
def route_matches_contract(route: str, route_format: str) -> bool:
    pattern_text = route_format.split(" ", 1)[0].strip()
    if not pattern_text:
        raise ValueError("route_format must contain a regex pattern.")

    return re.fullmatch(pattern_text, route, flags=re.IGNORECASE) is not None


# Extract the first completion flag from any nested response body structure.
def extract_completion_flag(payload: Any) -> str | None:
    if isinstance(payload, str):
        match = FLAG_PATTERN.search(payload)
        if match is None:
            return None

        return match.group(0)

    if isinstance(payload, dict):
        for value in payload.values():
            flag = extract_completion_flag(value)
            if flag is not None:
                return flag

        return None

    if isinstance(payload, list):
        for item in payload:
            flag = extract_completion_flag(item)
            if flag is not None:
                return flag

        return None

    return None


# Turn one final non-success response into a short workflow error message.
def describe_terminal_error(response: RailwayApiResponse) -> str | None:
    if response.http_status >= 400:
        return f"HTTP {response.http_status}: {extract_error_message(response.body)}"

    if isinstance(response.body, dict) and response.body.get("ok") is False:
        return extract_error_message(response.body)

    return None


# Extract the most useful human-readable error message from one API body.
def extract_error_message(payload: Any) -> str:
    if isinstance(payload, str):
        stripped_payload = payload.strip()
        if stripped_payload:
            return stripped_payload

        return "Request failed."

    if isinstance(payload, dict):
        for field_name in ("error", "message", "reason"):
            value = payload.get(field_name)
            if isinstance(value, str) and value.strip():
                return value

        return "Request failed."

    return "Request failed."
