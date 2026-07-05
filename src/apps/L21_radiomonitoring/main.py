# CLI entrypoint for the L21 radiomonitoring workflow.

from __future__ import annotations

import argparse
import json

from src.apps.L21_radiomonitoring.config import (
    ensure_runtime_directories,
    load_app_config,
    prepare_tls_environment,
)
from src.apps.L21_radiomonitoring.workflow import run_inspect, run_solve, run_submit


# Parse the small CLI used for inspect, solve, and submit modes.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="L21 radiomonitoring solution.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect", action="store_true", help="Capture live signals without model analysis.")
    mode.add_argument("--solve", action="store_true", help="Solve from cached signals without Hub submission.")
    mode.add_argument("--submit", action="store_true", help="Capture, solve, and transmit the final report.")
    parser.add_argument(
        "--from-cache",
        action="store_true",
        help="Use cached signals for submit mode instead of starting a new listening session.",
    )
    return parser.parse_args()


# Run the selected mode and print a compact JSON summary.
def main() -> None:
    args = parse_args()
    require_hub = bool(args.inspect or args.submit)
    require_openai = bool(args.solve or args.submit)
    config = load_app_config(require_hub=require_hub, require_openai=require_openai)
    ensure_runtime_directories(config.paths)
    if require_hub or require_openai:
        prepare_tls_environment(config.paths, required=True)

    if args.inspect:
        result = run_inspect(config)
    elif args.solve:
        result = run_solve(config)
    else:
        result = run_submit(config, from_cache=args.from_cache)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
