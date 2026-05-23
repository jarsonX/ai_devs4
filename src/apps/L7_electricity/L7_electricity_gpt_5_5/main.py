# Minimal CLI entrypoint for the L7 electricity application skeleton.

from __future__ import annotations

from src.apps.L7_electricity.L7_electricity_gpt_5_5.config import (
    AppConfig,
    ensure_runtime_directories,
    load_app_config,
)
from src.apps.L7_electricity.L7_electricity_gpt_5_5.workflow import ElectricityRunResult, run_guarded_workflow


# Build a compact console summary for the current workflow configuration.
def build_console_summary(config: AppConfig) -> str:
    lines = [
        f"App: {config.paths.app_dir.name}",
        f"Task: {config.hub.task_name}",
        f"Docs: {config.paths.docs_dir}",
        f"Data dir: {config.paths.data_dir}",
        f"Input dir: {config.paths.input_dir}",
        f"References dir: {config.paths.references_dir}",
        f"Output dir: {config.paths.output_dir}",
        f"Cache dir: {config.paths.cache_dir}",
        f"Request log: {config.paths.request_log_file}",
        f"Response log: {config.paths.response_log_file}",
        f"Reset on start: {config.runtime.reset_on_start}",
        f"Max rotations: {config.runtime.max_rotations}",
        f"Vision model: {config.vision.model_name}",
        "Status: ready to run guarded workflow",
    ]
    return "\n".join(lines)


# Build a compact summary for one completed guarded workflow run.
def build_run_summary(config: AppConfig, result: ElectricityRunResult) -> str:
    lines = [
        f"Run ID: {result.run_id}",
        f"Success: {result.success}",
        f"Reset used: {result.reset_used}",
        f"Max rotations: {result.max_rotations}",
        f"Planned rotations: {result.planned_rotations}",
        f"Executed rotations: {result.executed_rotations}",
        f"Guard triggered: {result.guard_triggered}",
        f"Run report: {config.paths.run_report_file}",
        f"Rotation plan: {config.paths.rotation_plan_file}",
        f"Diagnostics: {result.diagnostic_run_dir}",
    ]

    if result.completion_flag is not None:
        lines.append(f"Completion flag: {result.completion_flag}")

    if result.error_summary is not None:
        lines.append(f"Note: {result.error_summary}")

    return "\n".join(lines)


# Load configuration, run the guarded workflow, and print the outcome.
def main() -> None:
    config = load_app_config()
    ensure_runtime_directories(config.paths)
    print(build_console_summary(config))
    result = run_guarded_workflow(config)
    print("")
    print(build_run_summary(config, result))


if __name__ == "__main__":
    main()
