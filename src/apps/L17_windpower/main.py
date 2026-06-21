# CLI entrypoint for the L17 windpower workflow.

from __future__ import annotations

import argparse
import json

from src.apps.L17_windpower.config import (
    build_safe_config_summary,
    load_app_config,
    prepare_tls_environment,
)
from src.apps.L17_windpower.workflow import run_windpower_workflow


# Build the small CLI used for config checks and explicit live runs.
def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the L17_windpower workflow.")
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Print a secret-safe config summary without running the workflow.",
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Run the real timed Hub workflow.",
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
        parser.error("Use --check-config for a local check or --submit for the real timed Hub workflow.")

    config = load_app_config(require_hub=True)
    prepare_tls_environment(config.paths, required=True)
    result = run_windpower_workflow(config)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
