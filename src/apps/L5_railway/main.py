# Run the full deterministic railway route activation application.

from __future__ import annotations

from src.apps.L5_railway.config import AppPaths, HubConfig, build_app_paths, load_hub_config
from src.apps.L5_railway.help_contract import HelpContract, load_help_contract
from src.apps.L5_railway.logging_utils import save_workflow_artifacts
from src.apps.L5_railway.railway_client import RailwayApiClient
from src.apps.L5_railway.workflow import RouteActivationResult, activate_route


# Run one full railway activation pass and save all generated artifacts.
def run_application(
    paths: AppPaths,
    config: HubConfig,
    contract: HelpContract | None = None,
    client: RailwayApiClient | None = None,
) -> RouteActivationResult:
    selected_contract = contract or load_help_contract(paths)
    selected_client = client or RailwayApiClient(config)

    result = activate_route(selected_client, selected_contract)
    save_workflow_artifacts(paths, config, result)
    return result


# Build a compact console summary for one completed workflow result.
def build_console_summary(paths: AppPaths, result: RouteActivationResult) -> str:
    lines = [
        f"Route: {result.route}",
        f"Target status: {result.target_status}",
        f"Success: {result.success}",
        f"Steps executed: {len(result.steps)}",
        f"Request log: {paths.request_log_file}",
        f"Response log: {paths.response_log_file}",
        f"Run report: {paths.run_report_file}",
    ]

    if result.completion_flag is not None:
        lines.append(f"Completion flag: {result.completion_flag}")

    if result.terminal_error is not None:
        lines.append(f"Terminal error: {result.terminal_error}")

    return "\n".join(lines)


# Run the railway application from local configuration and print the outcome.
def main() -> None:
    paths = build_app_paths()
    config = load_hub_config()
    result = run_application(paths, config)
    print(build_console_summary(paths, result))


if __name__ == "__main__":
    main()
