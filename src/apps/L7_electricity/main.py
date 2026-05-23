# Minimal CLI entrypoint for the L7 electricity application skeleton.

from __future__ import annotations

from src.apps.L7_electricity.config import (
    AppConfig,
    ensure_runtime_directories,
    load_app_config,
)


# Build a compact console summary for the current skeleton configuration.
def build_console_summary(config: AppConfig) -> str:
    vision_model = config.runtime.vision_model or "not configured"

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
        f"Vision model: {vision_model}",
        "Status: skeleton ready",
    ]
    return "\n".join(lines)


# Load configuration and print a minimal readiness summary.
def main() -> None:
    config = load_app_config()
    ensure_runtime_directories(config.paths)
    print(build_console_summary(config))


if __name__ == "__main__":
    main()
