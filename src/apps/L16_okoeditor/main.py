# CLI entrypoint for the L16 deterministic okoeditor workflow.

from __future__ import annotations

import argparse
import json

from src.apps.L16_okoeditor.config import load_app_config, prepare_tls_environment
from src.apps.L16_okoeditor.oko_session import OkoWebClient
from src.apps.L16_okoeditor.verify_client import OkoVerifyClient
from src.apps.L16_okoeditor.workflow import run_okoeditor_workflow


# Parse the small CLI used for dry-run and live apply mode.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic L16 okoeditor workflow.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Send live updates and the final done action. Default mode is dry-run only.",
    )
    return parser.parse_args()


# Run the deterministic workflow and print a compact JSON summary.
def main() -> None:
    args = parse_args()
    config = load_app_config(require_verify_api=True, require_oko_web=True)
    prepare_tls_environment(config.paths, required=True)

    if config.oko_web is None or config.verify_api is None:
        raise ValueError("Both OKO web and verify API configuration are required.")

    reader = OkoWebClient(
        config.oko_web,
        timeout_seconds=config.runtime.request_timeout_seconds,
        max_page_fetches=config.runtime.max_page_fetches,
    )
    verifier = OkoVerifyClient(
        config.verify_api,
        timeout_seconds=config.runtime.request_timeout_seconds,
        max_requests=config.runtime.max_planned_writes + 1,
    )

    result = run_okoeditor_workflow(
        config,
        apply_updates=args.apply,
        reader=reader,
        verify_client=verifier,
    )
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
