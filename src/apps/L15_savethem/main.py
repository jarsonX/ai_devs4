# CLI entrypoint for the L15 discovery-agent workflow.

from __future__ import annotations

import argparse
import json

from src.apps.L15_savethem.config import build_safe_config_summary, load_app_config
from src.apps.L15_savethem.workflow import run_savethem_workflow


# Build the small CLI used for local checks and optional live runs.
def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the L15_savethem workflow.")
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Print a secret-safe config summary without running the workflow.",
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Allow the workflow to submit the final answer to the Hub.",
    )
    return parser


# Run the requested CLI action and print a JSON summary.
def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    if args.check_config:
        config = load_app_config(
            require_llm=False,
            require_external_api=False,
        )
        print(json.dumps(build_safe_config_summary(config), ensure_ascii=False, indent=2))
        return

    config = load_app_config(
        require_llm=True,
        require_external_api=True,
    )
    result = run_savethem_workflow(
        config,
        submission_enabled=args.submit,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
