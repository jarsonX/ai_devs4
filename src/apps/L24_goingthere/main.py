# CLI entrypoint for the guarded L24 goingthere workflow.

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.apps.L24_goingthere.api_client import GoingThereClient
from src.apps.L24_goingthere.config import (
    RuntimeConfig,
    build_paths,
    load_hub_config,
    load_openai_config,
    prepare_tls_environment,
)
from src.apps.L24_goingthere.evaluation import run_classifier_evaluation
from src.apps.L24_goingthere.llm_gateway import RadioHintClassifier
from src.apps.L24_goingthere.models import LoggedExchange
from src.apps.L24_goingthere.workflow import GoingThereWorkflow


# Parse explicit network modes while keeping local dry-run as the default.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Semantic radio classification with deterministic L24 movement."
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--submit",
        action="store_true",
        help="Run one guarded game using OpenAI and the course API.",
    )
    modes.add_argument(
        "--check-classifier",
        action="store_true",
        help="Run the bounded OpenAI semantic evaluation without contacting the Hub.",
    )
    return parser.parse_args()


# Write JSON runtime artifacts with stable UTF-8 formatting.
def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# Convert masked exchanges into JSON-safe report records.
def exchanges_to_dict(exchanges: list[LoggedExchange]) -> list[dict[str, Any]]:
    return [exchange.to_dict() for exchange in exchanges]


# Return a local description without loading secrets or contacting the Hub.
def run_dry_run() -> dict[str, object]:
    return {
        "status": "ready",
        "mode": "dry-run",
        "network_used": False,
        "live_command": (
            ".\\venv\\Scripts\\python.exe "
            "-m src.apps.L24_goingthere.main --submit"
        ),
        "classifier_check_command": (
            ".\\venv\\Scripts\\python.exe "
            "-m src.apps.L24_goingthere.main --check-classifier"
        ),
    }


# Run the bounded synthetic semantic check and preserve its diagnostic report.
def run_classifier_check() -> dict[str, object]:
    paths = build_paths()
    prepare_tls_environment(paths)
    runtime_config = RuntimeConfig()
    classifier = RadioHintClassifier(load_openai_config(), runtime_config)
    result = run_classifier_evaluation(classifier)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = paths.output_dir / f"classifier_eval_{stamp}.json"
    write_json(
        report_path,
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "result": result,
        },
    )
    return {
        "status": result["status"],
        "passed_cases": result["passed_cases"],
        "total_cases": result["total_cases"],
        "model_requests": result["model_requests"],
        "report_path": str(report_path.relative_to(paths.repo_root)),
    }


# Execute one guarded live game and preserve the complete diagnostic trace.
def run_submit() -> dict[str, object]:
    paths = build_paths()
    prepare_tls_environment(paths)
    runtime_config = RuntimeConfig()
    client = GoingThereClient(load_hub_config(), runtime_config)
    classifier = RadioHintClassifier(load_openai_config(), runtime_config)
    workflow = GoingThereWorkflow(client, classifier)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = paths.output_dir / f"run_report_{stamp}.json"
    exchanges_path = paths.logs_dir / f"exchanges_{stamp}.json"

    try:
        result = workflow.run()
    except Exception as error:
        result = {
            "status": "failed",
            "error_type": type(error).__name__,
            "error": str(error),
            "request_count": client.request_count(),
            "model_request_count": classifier.request_count(),
        }
        write_json(
            exchanges_path,
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "exchanges": exchanges_to_dict(client.exchanges()),
            },
        )
        write_json(
            report_path,
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "result": result,
                "classifications": classifier.records(),
                "exchanges_path": str(exchanges_path.relative_to(paths.repo_root)),
            },
        )
        raise

    write_json(
        exchanges_path,
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "exchanges": exchanges_to_dict(client.exchanges()),
        },
    )
    write_json(
        report_path,
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "result": result,
            "classifications": classifier.records(),
            "exchanges_path": str(exchanges_path.relative_to(paths.repo_root)),
        },
    )
    return {
        **result,
        "report_path": str(report_path.relative_to(paths.repo_root)),
        "exchanges_path": str(exchanges_path.relative_to(paths.repo_root)),
    }


# Run only the explicitly selected mode and print its compact result.
def main() -> None:
    args = parse_args()
    if args.submit:
        result = run_submit()
    elif args.check_classifier:
        result = run_classifier_check()
    else:
        result = run_dry_run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
