# JSON report writing for the L11 evaluation workflow.

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.apps.L11_evaluation.config import TASK_NAME
from src.apps.L11_evaluation.models import EvaluationAnswer, MeasurementFinding, SensorIssue


# Convert one deterministic issue into a JSON-safe dictionary.
def sensor_issue_to_dict(issue: SensorIssue) -> dict[str, Any]:
    return {
        "file_id": issue.file_id,
        "kind": issue.kind,
        "message": issue.message,
        "field": issue.field,
        "value": issue.value,
    }


# Convert one deterministic finding into a JSON-safe dictionary.
def measurement_finding_to_dict(finding: MeasurementFinding) -> dict[str, Any]:
    return {
        "file_id": finding.file_id,
        "sensor_type": finding.sensor_type,
        "measurements_ok": finding.measurements_ok,
        "active_sensors": list(finding.active_sensors),
        "active_fields": list(finding.active_fields),
        "issues": [sensor_issue_to_dict(issue) for issue in finding.issues],
    }


# Count issue kinds in stable alphabetical order for easy diffs between runs.
def build_issue_counts_by_kind(issues: list[SensorIssue]) -> dict[str, int]:
    issue_counts = Counter(issue.kind for issue in issues)
    return {
        issue_kind: issue_counts[issue_kind]
        for issue_kind in sorted(issue_counts)
    }


# Build the full deterministic scan report written before any LLM work starts.
def build_deterministic_findings_report(
    findings: list[MeasurementFinding],
    *,
    loader_issues: list[SensorIssue] | None = None,
) -> dict[str, Any]:
    loader_issues = loader_issues or []
    all_finding_issues = [
        issue
        for finding in findings
        for issue in finding.issues
    ]
    all_issues = [*loader_issues, *all_finding_issues]

    return {
        "summary": {
            "record_count": len(findings),
            "valid_record_count": sum(1 for finding in findings if finding.measurements_ok),
            "invalid_record_count": sum(1 for finding in findings if not finding.measurements_ok),
            "loader_issue_count": len(loader_issues),
            "deterministic_issue_count": len(all_finding_issues),
            "total_issue_count": len(all_issues),
            "issue_counts_by_kind": build_issue_counts_by_kind(all_issues),
        },
        "loader_issues": [sensor_issue_to_dict(issue) for issue in loader_issues],
        "findings": [measurement_finding_to_dict(finding) for finding in findings],
    }


# Write one JSON artifact with stable formatting under the app output directory.
def write_json_report(output_path: Path, payload: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


# Persist deterministic findings so later steps can inspect them without rerunning the scan.
def write_deterministic_findings_report(
    output_path: Path,
    findings: list[MeasurementFinding],
    *,
    loader_issues: list[SensorIssue] | None = None,
) -> dict[str, Any]:
    report_payload = build_deterministic_findings_report(
        findings,
        loader_issues=loader_issues,
    )
    write_json_report(output_path, report_payload)
    return report_payload


# Convert the final answer into the local non-secret payload shape used before Hub submission.
def build_final_answer_payload(
    answer: EvaluationAnswer,
    *,
    task_name: str = TASK_NAME,
) -> dict[str, Any]:
    return {
        "task": task_name,
        "answer": {
            "recheck": answer.recheck,
        },
    }


# Persist the final local answer without adding a real API key.
def write_final_answer_report(
    output_path: Path,
    answer: EvaluationAnswer,
    *,
    task_name: str = TASK_NAME,
) -> dict[str, Any]:
    payload = build_final_answer_payload(
        answer,
        task_name=task_name,
    )
    write_json_report(output_path, payload)
    return payload
