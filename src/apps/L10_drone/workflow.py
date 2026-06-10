# Bounded LLM-assisted repair workflow for the L10 drone task.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from src.apps.L10_drone.api_docs import build_docs_context
from src.apps.L10_drone.config import AppConfig, build_safe_config_summary, ensure_runtime_directories
from src.apps.L10_drone.hub_client import (
    HubClient,
    VerifyRequestGuard,
    extract_flag,
    hub_response_for_log,
)
from src.apps.L10_drone.planner import (
    DroneInstructionPlan,
    DroneMissionPlanner,
    ModelRequestGuard,
    PlannerRequest,
    plan_for_log,
)
from src.apps.L10_drone.run_log import RunLog, append_event, create_run_log
from src.apps.L10_drone.validation import validate_instruction_plan, validation_for_log


# Define the planner behavior needed by the workflow so tests can use fakes.
class PlannerProtocol(Protocol):
    # Return one initial or repaired drone instruction plan.
    def plan(self, request: PlannerRequest) -> DroneInstructionPlan:
        ...


# Define the Hub behavior needed by the workflow so tests can use fakes.
class HubClientProtocol(Protocol):
    # Submit instructions and return a masked request plus Hub response.
    def verify_instructions(self, instructions: list[str]) -> tuple[dict[str, Any], Any]:
        ...


# Preserve the final workflow status for callers and tests.
@dataclass(frozen=True)
class WorkflowResult:
    status: str
    reason: str
    attempts_used: int
    run_log_path: str
    flag_found: bool = False


# Return secret values that must never be written to logs.
def secret_values_from_config(config: AppConfig) -> list[str]:
    secrets: list[str] = []
    if config.llm:
        secrets.append(config.llm.api_key)
    if config.hub:
        secrets.append(config.hub.api_key)
    return secrets


# Run the bounded attempt and repair loop.
def run_drone_workflow(
    config: AppConfig,
    *,
    planner: PlannerProtocol | None = None,
    hub_client: HubClientProtocol | None = None,
    run_log: RunLog | None = None,
) -> WorkflowResult:
    if config.llm is None:
        raise ValueError("LLM configuration is required.")
    if config.hub is None:
        raise ValueError("Hub configuration is required.")

    ensure_runtime_directories(config.paths)
    active_log = run_log or create_run_log(config.paths.logs_dir)
    secrets = secret_values_from_config(config)
    docs_context = build_docs_context(config.paths.drone_docs_file)
    active_planner = planner or DroneMissionPlanner(
        config.llm,
        guard=ModelRequestGuard(max_requests=config.runtime.max_verify_attempts),
    )
    active_hub = hub_client or HubClient(
        config.hub,
        timeout_seconds=config.runtime.request_timeout_seconds,
        guard=VerifyRequestGuard(max_requests=config.runtime.max_verify_attempts),
    )

    append_event(
        active_log,
        event="run_started",
        data={
            "config": build_safe_config_summary(config),
            "drone_docs_file": str(config.paths.drone_docs_file.relative_to(config.paths.repo_root)),
            "drone_map_file": str(config.paths.drone_map_file.relative_to(config.paths.repo_root)),
        },
        secret_values=secrets,
    )

    previous_instructions: list[str] | None = None
    hub_feedback: Any | None = None

    for attempt in range(1, config.runtime.max_verify_attempts + 1):
        request = PlannerRequest(
            attempt=attempt,
            docs_context=docs_context,
            mission=config.mission,
            max_attempts=config.runtime.max_verify_attempts,
            previous_instructions=previous_instructions,
            hub_feedback=hub_feedback,
        )
        plan = active_planner.plan(request)
        append_event(
            active_log,
            event="agent_plan",
            attempt=attempt,
            data=plan_for_log(plan),
            secret_values=secrets,
        )

        validation = validate_instruction_plan(
            plan,
            config.runtime,
            mission=config.mission,
            secret_values=secrets,
            previous_instructions=previous_instructions if attempt > 1 else None,
        )
        append_event(
            active_log,
            event="validation_result",
            attempt=attempt,
            data=validation_for_log(validation),
            secret_values=secrets,
        )
        if not validation.passed:
            return _finish(
                active_log,
                status="failed_validation",
                reason="Planner output failed local validation.",
                attempts_used=attempt,
                secret_values=secrets,
            )

        masked_request, hub_response = active_hub.verify_instructions(plan.instructions)
        append_event(
            active_log,
            event="hub_request",
            attempt=attempt,
            data=masked_request,
            secret_values=secrets,
        )
        response_log_payload = hub_response_for_log(hub_response)
        append_event(
            active_log,
            event="hub_response",
            attempt=attempt,
            data=response_log_payload,
            secret_values=secrets,
        )

        flag = extract_flag(hub_response.payload) or extract_flag(hub_response.text)
        if flag:
            return _finish(
                active_log,
                status="solved",
                reason="Hub returned a flag.",
                attempts_used=attempt,
                flag_found=True,
                secret_values=secrets,
            )

        previous_instructions = plan.instructions
        hub_feedback = {
            "status_code": hub_response.status_code,
            "payload": hub_response.payload,
            "text": hub_response.text,
        }

    return _finish(
        active_log,
        status="blocked",
        reason="Attempt limit reached before the Hub returned a flag.",
        attempts_used=config.runtime.max_verify_attempts,
        secret_values=secrets,
    )


# Log and return one terminal workflow result.
def _finish(
    run_log: RunLog,
    *,
    status: str,
    reason: str,
    attempts_used: int,
    flag_found: bool = False,
    secret_values: list[str] | None = None,
) -> WorkflowResult:
    append_event(
        run_log,
        event="run_finished",
        data={"status": status, "reason": reason, "flag_found": flag_found},
        attempt=attempts_used,
        secret_values=secret_values,
    )
    return WorkflowResult(
        status=status,
        reason=reason,
        attempts_used=attempts_used,
        run_log_path=str(run_log.path),
        flag_found=flag_found,
    )
