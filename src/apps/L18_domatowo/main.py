# CLI entrypoint for the L18 Domatowo workflow.

from __future__ import annotations

import argparse
import json

from src.apps.L18_domatowo.config import (
    build_safe_config_summary,
    load_app_config,
    prepare_tls_environment,
)
from src.apps.L18_domatowo.workflow import run_domatowo_workflow


# Build the small CLI used for config checks and explicit live runs.
def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the L18_domatowo workflow.")
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Print a secret-safe config summary without calling the Hub.",
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Run the real Hub workflow.",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Continue the current Hub board state instead of resetting first.",
    )
    return parser


# Run the requested CLI action and print a JSON summary.
def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    if args.check_config:
        config = load_app_config(require_hub=False)
        print(json.dumps(build_safe_config_summary(config), ensure_ascii=False, indent=2))
        return

    if not args.submit:
        parser.error("Use --check-config for a local check or --submit for the real Hub workflow.")

    config = load_app_config(require_hub=True)
    prepare_tls_environment(config.paths, required=False)
    result = run_domatowo_workflow(config, reset_board=not args.no_reset)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
