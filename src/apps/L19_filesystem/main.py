# CLI entrypoint for the L19 deterministic filesystem workflow.

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.apps.L19_filesystem.config import (
    build_safe_config_summary,
    ensure_runtime_directories,
    load_app_config,
    prepare_tls_environment,
)
from src.apps.L19_filesystem.payloads import (
    build_batch_answer,
    build_solution_summary,
)
from src.apps.L19_filesystem.verify_client import (
    FilesystemVerifyClient,
    LoggedExchange,
    response_contains_flag,
)


# Parse the small CLI used for dry-run and live submit mode.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic L19 filesystem solution.")
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Send live reset, batch create, and done calls to the Hub.",
    )
    return parser.parse_args()


# Write JSON with stable formatting for local learning artifacts.
def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# Convert a sequence of exchanges into runtime JSON data.
def exchanges_to_dict(exchanges: list[LoggedExchange]) -> list[dict[str, Any]]:
    return [exchange.to_dict() for exchange in exchanges]


# Run the local dry-run path and return a compact summary.
def run_dry_run() -> dict[str, Any]:
    config = load_app_config(require_hub=False)
    ensure_runtime_directories(config.paths)

    operations = build_batch_answer()
    summary = {
        "mode": "dry-run",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config": build_safe_config_summary(config),
        "solution": build_solution_summary(),
        "operations": operations,
    }
    output_path = config.paths.output_dir / "planned_filesystem.json"
    write_json(output_path, summary)
    return {
        "status": "dry_run_ok",
        "operation_count": len(operations),
        "planned_filesystem_path": str(output_path.relative_to(config.paths.repo_root)),
    }


# Run the live Hub submission path and preserve raw API feedback in runtime data.
def run_submit() -> dict[str, Any]:
    config = load_app_config(require_hub=True)
    ensure_runtime_directories(config.paths)
    prepare_tls_environment(config.paths, required=True)
    if config.hub is None:
        raise ValueError("Hub config is required for submit mode.")

    operations = build_batch_answer()
    client = FilesystemVerifyClient(
        config.hub,
        timeout_seconds=config.runtime.request_timeout_seconds,
        max_requests=config.runtime.max_verify_requests,
    )

    exchanges: list[LoggedExchange] = [
        client.help(),
        client.reset(),
        client.apply_batch(operations),
        client.done(),
    ]
    final_response = exchanges[-1].response

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_report_path = config.paths.output_dir / f"run_report_{stamp}.json"
    final_response_path = config.paths.output_dir / f"final_response_{stamp}.json"

    write_json(
        run_report_path,
        {
            "mode": "submit",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "config": build_safe_config_summary(config),
            "operation_count": len(operations),
            "request_count": client.request_count(),
            "flag_found": response_contains_flag(final_response),
            "exchanges": exchanges_to_dict(exchanges),
        },
    )
    write_json(
        final_response_path,
        {
            "status_code": final_response.status_code,
            "payload": final_response.payload,
            "text": final_response.text,
            "flag_found": response_contains_flag(final_response),
        },
    )

    return {
        "status": "solved" if response_contains_flag(final_response) else "submitted",
        "operation_count": len(operations),
        "request_count": client.request_count(),
        "run_report_path": str(run_report_path.relative_to(config.paths.repo_root)),
        "final_response_path": str(final_response_path.relative_to(config.paths.repo_root)),
        "flag_found": response_contains_flag(final_response),
        "final_payload": final_response.payload,
        "final_text": final_response.text,
    }


# Run the selected mode and print a compact JSON summary.
def main() -> None:
    args = parse_args()
    result = run_submit() if args.submit else run_dry_run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
