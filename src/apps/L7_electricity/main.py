# Minimal CLI entrypoint for the L7 electricity application skeleton.

from __future__ import annotations

from src.apps.L7_electricity.config import AppConfig, load_app_config


# Build a compact console summary for the current skeleton configuration.
def build_console_summary(config: AppConfig) -> str:
    vision_model = config.runtime.vision_model or "not configured"

    lines = [
        f"App: {config.metadata.app_dir.name}",
        f"Task: {config.hub.task_name}",
        f"Docs: {config.metadata.docs_dir}",
        f"Reset on start: {config.runtime.reset_on_start}",
        f"Max rotations: {config.runtime.max_rotations}",
        f"Vision model: {vision_model}",
        "Status: skeleton ready",
    ]
    return "\n".join(lines)


# Load configuration and print a minimal readiness summary.
def main() -> None:
    config = load_app_config()
    print(build_console_summary(config))


if __name__ == "__main__":
    main()
