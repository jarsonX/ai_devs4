# This module exposes the Step 8 CLI entrypoint for the mailbox workbench.

from __future__ import annotations

import argparse
import json

from src.apps.L9_mailbox.agent import MailboxInvestigatorResult, run_mailbox_investigator
from src.apps.L9_mailbox.config import build_safe_config_summary, load_app_config


# Parse the mailbox workbench CLI flags, including the explicit submit guard.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the L9 mailbox workbench with optional guarded Hub submission.",
    )
    parser.add_argument(
        "--workbench",
        action="store_true",
        help="Run the bounded mailbox investigator workbench.",
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Allow the investigator to use guarded Hub submission after local validation.",
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print a secret-safe config summary before the run starts.",
    )
    return parser.parse_args()


# Build a short human-readable summary from one completed workbench result.
def build_run_summary(result: MailboxInvestigatorResult) -> str:
    return json.dumps(
        {
            "status": result.status,
            "found_values": {
                "date": result.found_values.date,
                "password": result.found_values.password,
                "confirmation_code": result.found_values.confirmation_code,
            },
            "iterations_used": result.iterations_used,
            "model_calls_used": result.model_calls_used,
            "tool_calls_used": result.tool_calls_used,
            "stop_reason": result.stop_reason,
            "report_path": str(result.report_path) if result.report_path else None,
        },
        ensure_ascii=False,
        indent=2,
    )


# Run the selected mailbox workbench mode and return a shell-friendly exit code.
def main() -> int:
    args = parse_args()
    if not args.workbench:
        raise ValueError("Use --workbench to run the mailbox workbench flow.")

    config = load_app_config(require_external_api=True, require_llm=True)
    if args.print_config:
        print(json.dumps(build_safe_config_summary(config), ensure_ascii=False, indent=2))

    result = run_mailbox_investigator(
        config,
        submission_enabled=args.submit,
        write_report=True,
    )
    print(build_run_summary(result))

    if args.submit and result.status != "solved":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
