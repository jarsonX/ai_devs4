# CLI entrypoint for the bounded L12 firmware agent.

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from typing import Any

from src.apps.L12_firmware.agent import FirmwareAgentResult, run_firmware_agent
from src.apps.L12_firmware.config import (
    AppConfig,
    build_safe_config_summary,
    load_app_config,
)


# Parse an explicit local-check or live-run mode without implicit network access.
def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the bounded L12 firmware agent.",
    )
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--check-config",
        action="store_true",
        help="Print secret-safe local configuration without external calls.",
    )
    mode_group.add_argument(
        "--live",
        action="store_true",
        help="Allow the bounded agent to call OpenAI and the firmware shell API.",
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Additionally allow one guarded Hub submission during --live.",
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print secret-safe configuration before a live run.",
    )
    args = parser.parse_args(argv)
    if args.submit and not args.live:
        parser.error("--submit requires --live.")
    return args


# Build a compact stdout summary while the full response remains in runtime data.
def build_run_summary(result: FirmwareAgentResult) -> str:
    return json.dumps(
        {
            "status": result.status,
            "stop_reason": result.stop_reason,
            "confirmation": result.confirmation,
            "model_calls_used": result.model_calls_used,
            "tool_calls_used": result.tool_calls_used,
            "total_reported_tokens": result.total_reported_tokens,
            "report_path": str(result.report_path) if result.report_path else None,
        },
        ensure_ascii=False,
        indent=2,
    )


# Execute one already parsed CLI mode with injectable dependencies for local tests.
def run_cli(
    args: argparse.Namespace,
    *,
    config_loader: Callable[..., AppConfig] = load_app_config,
    agent_runner: Callable[..., FirmwareAgentResult] = run_firmware_agent,
) -> int:
    if args.check_config:
        config = config_loader(
            require_external_api=False,
            require_llm=False,
        )
        print(json.dumps(build_safe_config_summary(config), ensure_ascii=False, indent=2))
        return 0

    config = config_loader(
        require_external_api=True,
        require_llm=True,
    )
    if args.print_config:
        print(json.dumps(build_safe_config_summary(config), ensure_ascii=False, indent=2))

    result = agent_runner(
        config,
        submission_enabled=args.submit,
        write_report=True,
    )
    print(build_run_summary(result))

    if args.submit and result.status != "solved":
        return 1
    return 0


# Parse command-line arguments and return a shell-friendly exit code.
def main(argv: Sequence[str] | None = None) -> int:
    return run_cli(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
