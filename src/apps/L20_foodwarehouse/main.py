# CLI entrypoint for the L20 deterministic foodwarehouse workflow.

from __future__ import annotations

import argparse
import json

from src.apps.L20_foodwarehouse.config import (
    ensure_runtime_directories,
    load_app_config,
    prepare_tls_environment,
)
from src.apps.L20_foodwarehouse.workflow import run_dry_run, run_submit
from src.apps.L20_foodwarehouse.workflow import run_inspect_remote


# Parse the small CLI used for dry-run and live submit mode.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic L20 foodwarehouse solution.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--submit",
        action="store_true",
        help="Send live database, signature, order, and done calls to the Hub.",
    )
    mode.add_argument(
        "--inspect-remote",
        action="store_true",
        help="Read live help and SQLite tables without changing remote orders.",
    )
    return parser.parse_args()


# Run the selected mode and print a compact JSON summary.
def main() -> None:
    args = parse_args()
    needs_hub = args.submit or args.inspect_remote
    config = load_app_config(require_hub=needs_hub)
    ensure_runtime_directories(config.paths)
    if needs_hub:
        prepare_tls_environment(config.paths, required=True)
    if args.submit:
        result = run_submit(config)
    elif args.inspect_remote:
        result = run_inspect_remote(config)
    else:
        result = run_dry_run(config)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
