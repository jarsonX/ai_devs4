# CLI entrypoint for the L11 evaluation workflow.

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.apps.L11_evaluation.config import (
    AppConfig,
    AppPaths,
    LlmConfig,
    build_safe_config_summary,
    ensure_runtime_directories,
    load_app_config,
)
from src.apps.L11_evaluation.deterministic_validator import validate_sensor_records
from src.apps.L11_evaluation.hub_client import HubClient, VerifyRequestGuard, hub_response_for_log
from src.apps.L11_evaluation.loader import load_sensor_records
from src.apps.L11_evaluation.models import EvaluationAnswer, NoteClassification
from src.apps.L11_evaluation.note_cache import (
    build_record_note_hash_index,
    collect_unique_normalized_notes,
    find_uncached_notes,
    load_note_cache,
    save_note_cache,
)
from src.apps.L11_evaluation.note_classifier import (
    ModelRequestGuard,
    OperatorNoteClassifier,
    classify_and_merge_uncached_notes,
)
from src.apps.L11_evaluation.report_writer import (
    write_deterministic_findings_report,
    write_final_answer_report,
    write_json_report,
)
from src.apps.L11_evaluation.resolver import build_evaluation_answer


# Preserve the main workflow outputs in a test-friendly shape.
@dataclass(frozen=True)
class EvaluationWorkflowResult:
    answer: EvaluationAnswer
    record_count: int
    loader_issue_count: int
    invalid_record_count: int
    unique_note_count: int
    uncached_note_count: int
    cache_entry_count: int
    deterministic_findings_path: Path
    final_answer_path: Path
    cache_path: Path
    run_report_path: Path
    submission_requested: bool
    submission_performed: bool
    masked_verify_payload: dict[str, Any] | None = None
    hub_response_log: dict[str, Any] | None = None


# Parse the CLI flags for local scan mode or guarded submit mode.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the L11 evaluation workflow in local scan mode or guarded submit mode.",
    )
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--scan",
        action="store_true",
        help="Run the full local workflow and stop after local artifacts are written.",
    )
    mode_group.add_argument(
        "--submit",
        action="store_true",
        help="Run the full workflow and then perform guarded Hub verification.",
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print a secret-safe config summary before the run starts.",
    )
    return parser.parse_args()


# Build the real classifier only when uncached notes require a model call.
def build_note_classifier(config: LlmConfig, max_requests: int) -> OperatorNoteClassifier:
    return OperatorNoteClassifier(
        config,
        guard=ModelRequestGuard(max_requests=max_requests),
    )


# Build file-level note classifications from the cache keyed by note hash.
def build_note_classifications_by_file_id(
    note_hash_by_file_id: dict[str, str],
    cache: dict[str, NoteClassification],
) -> dict[str, NoteClassification]:
    note_classifications_by_file_id: dict[str, NoteClassification] = {}

    for file_id, note_hash in note_hash_by_file_id.items():
        note_classification = cache.get(note_hash)
        if note_classification is None:
            raise ValueError(f"Missing cached note classification for file_id {file_id}.")
        note_classifications_by_file_id[file_id] = note_classification

    return note_classifications_by_file_id


# Return repository-relative artifact paths for the final run report.
def build_artifact_paths(paths: AppPaths) -> dict[str, str]:
    return {
        "deterministic_findings_file": str(
            paths.deterministic_findings_file.relative_to(paths.repo_root)
        ),
        "final_answer_file": str(paths.final_answer_file.relative_to(paths.repo_root)),
        "operator_notes_cache_file": str(
            paths.operator_notes_cache_file.relative_to(paths.repo_root)
        ),
        "run_report_file": str(paths.run_report_file.relative_to(paths.repo_root)),
    }


# Persist one secret-safe workflow summary after scan or submit mode completes.
def write_run_report(
    config: AppConfig,
    result: EvaluationWorkflowResult,
) -> dict[str, Any]:
    report_payload = {
        "app": "L11_evaluation",
        "task": "evaluation",
        "mode": "submit" if result.submission_requested else "scan",
        "record_count": result.record_count,
        "loader_issue_count": result.loader_issue_count,
        "invalid_record_count": result.invalid_record_count,
        "unique_note_count": result.unique_note_count,
        "uncached_note_count": result.uncached_note_count,
        "cache_entry_count": result.cache_entry_count,
        "recheck_count": len(result.answer.recheck),
        "artifacts": build_artifact_paths(config.paths),
        "submission": {
            "requested": result.submission_requested,
            "performed": result.submission_performed,
            "masked_verify_payload": result.masked_verify_payload,
            "hub_response": result.hub_response_log,
        },
    }
    write_json_report(config.paths.run_report_file, report_payload)
    return report_payload


# Run the full local workflow, including note classification, and write local artifacts.
def run_scan_workflow(
    config: AppConfig,
    *,
    classifier: OperatorNoteClassifier | Any | None = None,
) -> EvaluationWorkflowResult:
    ensure_runtime_directories(config.paths)

    records, loader_issues = load_sensor_records(config.paths.sensors_dir)
    findings = validate_sensor_records(records)
    write_deterministic_findings_report(
        config.paths.deterministic_findings_file,
        findings,
        loader_issues=loader_issues,
    )

    note_cache = load_note_cache(config.paths.operator_notes_cache_file)
    unique_notes = collect_unique_normalized_notes(records)
    uncached_notes = find_uncached_notes(records, note_cache)

    active_classifier = classifier
    if uncached_notes:
        if active_classifier is None:
            if config.llm is None:
                raise ValueError(
                    "OPENAI_API_KEY is required to classify uncached notes during --scan."
                )
            active_classifier = build_note_classifier(
                config.llm,
                config.runtime.max_note_classification_calls,
            )

        note_cache = classify_and_merge_uncached_notes(
            active_classifier,
            note_cache,
            uncached_notes,
            batch_size=config.runtime.note_batch_size,
        )

    save_note_cache(config.paths.operator_notes_cache_file, note_cache)

    note_hash_by_file_id = build_record_note_hash_index(records)
    note_classifications_by_file_id = build_note_classifications_by_file_id(
        note_hash_by_file_id,
        note_cache,
    )

    answer = build_evaluation_answer(findings, note_classifications_by_file_id)
    write_final_answer_report(config.paths.final_answer_file, answer)

    result = EvaluationWorkflowResult(
        answer=answer,
        record_count=len(records),
        loader_issue_count=len(loader_issues),
        invalid_record_count=sum(1 for finding in findings if not finding.measurements_ok),
        unique_note_count=len(unique_notes),
        uncached_note_count=len(uncached_notes),
        cache_entry_count=len(note_cache),
        deterministic_findings_path=config.paths.deterministic_findings_file,
        final_answer_path=config.paths.final_answer_file,
        cache_path=config.paths.operator_notes_cache_file,
        run_report_path=config.paths.run_report_file,
        submission_requested=False,
        submission_performed=False,
    )
    write_run_report(config, result)
    return result


# Run the full workflow and then submit the final answer through the guarded Hub client.
def run_submit_workflow(
    config: AppConfig,
    *,
    classifier: OperatorNoteClassifier | Any | None = None,
    hub_client: HubClient | Any | None = None,
) -> EvaluationWorkflowResult:
    scan_result = run_scan_workflow(config, classifier=classifier)

    if hub_client is None:
        if config.hub is None:
            raise ValueError("AI_DEVS_API_KEY and HUB_VERIFY_URL are required for --submit.")
        hub_client = HubClient(
            config.hub,
            timeout_seconds=config.runtime.request_timeout_seconds,
            guard=VerifyRequestGuard(max_requests=config.runtime.max_verify_requests),
        )

    masked_verify_payload, hub_response = hub_client.verify_answer(scan_result.answer)
    result = EvaluationWorkflowResult(
        answer=scan_result.answer,
        record_count=scan_result.record_count,
        loader_issue_count=scan_result.loader_issue_count,
        invalid_record_count=scan_result.invalid_record_count,
        unique_note_count=scan_result.unique_note_count,
        uncached_note_count=scan_result.uncached_note_count,
        cache_entry_count=scan_result.cache_entry_count,
        deterministic_findings_path=scan_result.deterministic_findings_path,
        final_answer_path=scan_result.final_answer_path,
        cache_path=scan_result.cache_path,
        run_report_path=scan_result.run_report_path,
        submission_requested=True,
        submission_performed=True,
        masked_verify_payload=masked_verify_payload,
        hub_response_log=hub_response_for_log(hub_response),
    )
    write_run_report(config, result)
    return result


# Build a short JSON summary printed to stdout after one completed run.
def build_run_summary(result: EvaluationWorkflowResult) -> str:
    return json.dumps(
        {
            "record_count": result.record_count,
            "loader_issue_count": result.loader_issue_count,
            "invalid_record_count": result.invalid_record_count,
            "unique_note_count": result.unique_note_count,
            "uncached_note_count": result.uncached_note_count,
            "cache_entry_count": result.cache_entry_count,
            "recheck_count": len(result.answer.recheck),
            "submission_requested": result.submission_requested,
            "submission_performed": result.submission_performed,
            "artifacts": {
                "deterministic_findings_path": str(result.deterministic_findings_path),
                "final_answer_path": str(result.final_answer_path),
                "cache_path": str(result.cache_path),
                "run_report_path": str(result.run_report_path),
            },
        },
        ensure_ascii=False,
        indent=2,
    )


# Run the selected CLI mode and return a shell-friendly exit code.
def main() -> int:
    args = parse_args()
    config = load_app_config(
        require_hub=args.submit,
        require_llm=False,
    )

    if args.print_config:
        print(json.dumps(build_safe_config_summary(config), ensure_ascii=False, indent=2))

    if args.scan:
        result = run_scan_workflow(config)
    else:
        result = run_submit_workflow(config)

    print(build_run_summary(result))

    if result.submission_performed and result.hub_response_log:
        if result.hub_response_log["status_code"] >= 400:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
