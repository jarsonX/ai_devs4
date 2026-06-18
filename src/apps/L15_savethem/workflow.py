# End-to-end workflow orchestration for the L15 discovery agent.

from __future__ import annotations

from typing import Any

from src.apps.L15_savethem.agent import run_explorer_agent
from src.apps.L15_savethem.api_client import CourseApiClient
from src.apps.L15_savethem.config import AppConfig, apply_repository_tls_ca_setup, ensure_runtime_directories
from src.apps.L15_savethem.knowledge import attempt_ready_recovery, build_mission_knowledge
from src.apps.L15_savethem.models import WorkflowResult
from src.apps.L15_savethem.report_writer import save_knowledge_report, save_route_report, save_run_report
from src.apps.L15_savethem.solver import solve_route


# Run the bounded explorer, deterministic solver, and optional verify flow.
def run_savethem_workflow(
    config: AppConfig,
    *,
    llm_client: Any | None = None,
    api_client: CourseApiClient | None = None,
    submission_enabled: bool = False,
) -> WorkflowResult:
    ensure_runtime_directories(config.paths)
    apply_repository_tls_ca_setup(config.paths)

    if api_client is None:
        if config.external_api is None:
            raise ValueError("External API config is required when no api_client is injected.")
        api_client = CourseApiClient(
            config.external_api,
            timeout_seconds=config.runtime.request_timeout_seconds,
        )

    exploration_result = run_explorer_agent(
        config,
        llm_client=llm_client,
        api_client=api_client,
    )
    exploration_result = attempt_ready_recovery(exploration_result) or exploration_result

    if exploration_result.status != "ready":
        result = WorkflowResult(
            status="blocked",
            exploration_status=exploration_result.status,
            knowledge=None,
            route_plan=None,
            report_path=str(config.paths.run_report_file.relative_to(config.paths.repo_root)),
            model_calls_used=exploration_result.model_calls_used,
            tool_calls_used=exploration_result.tool_calls_used,
            stop_reason=exploration_result.stop_reason,
        )
        save_run_report(
            config.paths,
            {
                "result": result.to_dict(),
                "exploration": exploration_result.to_dict(),
            },
        )
        return result

    knowledge = build_mission_knowledge(exploration_result)
    save_knowledge_report(config.paths, knowledge.to_dict())
    route_plan = solve_route(
        knowledge,
        starting_fuel=config.runtime.starting_fuel,
        starting_food=config.runtime.starting_food,
    )
    save_route_report(config.paths, route_plan.to_dict())

    submission_response: dict[str, Any] | None = None
    if submission_enabled:
        verify_exchange = api_client.verify_answer(list(route_plan.commands))
        submission_response = {
            "request": verify_exchange.request,
            "response": verify_exchange.response.to_dict(),
        }

    result = WorkflowResult(
        status="solved" if route_plan.reached_goal else "blocked",
        exploration_status=exploration_result.status,
        knowledge=knowledge,
        route_plan=route_plan,
        report_path=str(config.paths.run_report_file.relative_to(config.paths.repo_root)),
        model_calls_used=exploration_result.model_calls_used,
        tool_calls_used=exploration_result.tool_calls_used,
        submission_response=submission_response,
        stop_reason=exploration_result.stop_reason,
        route_blocker=None if route_plan.reached_goal else "solver did not reach the goal",
    )
    save_run_report(
        config.paths,
        {
            "result": result.to_dict(),
            "exploration": exploration_result.to_dict(),
            "knowledge": knowledge.to_dict(),
            "route_plan": route_plan.to_dict(),
            "submission_response": submission_response,
        },
    )
    return result
