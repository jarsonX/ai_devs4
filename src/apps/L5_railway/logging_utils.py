# Save masked railway workflow artifacts for later review.

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.apps.L5_railway.config import AppPaths, HubConfig
from src.apps.L5_railway.railway_client import build_action_payload
from src.apps.L5_railway.workflow import RouteActivationResult, WorkflowStepResult


REDACTED = "***REDACTED***"


# Save all route-activation artifacts to the configured output files.
def save_workflow_artifacts(
    paths: AppPaths,
    config: HubConfig,
    result: RouteActivationResult,
) -> None:
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl_file(paths.request_log_file, build_request_log_records(config, result))
    write_jsonl_file(paths.response_log_file, build_response_log_records(result))
    paths.run_report_file.write_text(build_run_report(result), encoding="utf-8")


# Build masked request log records from one workflow result.
def build_request_log_records(
    config: HubConfig,
    result: RouteActivationResult,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for step_index, step in enumerate(result.steps, start=1):
        payload = build_action_payload(config, step.action, dict(step.request_fields))
        records.append(
            {
                "step_index": step_index,
                "action": step.action,
                "sent_at": current_timestamp(),
                "url_env": "HUB_VERIFY_URL",
                "payload": mask_payload_for_storage(payload),
            }
        )

    return records


# Build response log records from one workflow result.
def build_response_log_records(result: RouteActivationResult) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for step_index, step in enumerate(result.steps, start=1):
        records.append(
            {
                "step_index": step_index,
                "action": step.action,
                "received_at": current_timestamp(),
                "http_status": step.response.http_status,
                "attempts_used": step.response.attempts_used,
                "headers": step.response.headers,
                "body": step.response.body,
            }
        )

    return records


# Build one compact markdown report for a workflow run.
def build_run_report(result: RouteActivationResult) -> str:
    lines = [
        "# L5 Railway Run Report",
        "",
        f"- Generated at: `{current_timestamp()}`",
        f"- Route: `{result.route}`",
        f"- Target status: `{result.target_status}`",
        f"- Success: `{result.success}`",
        f"- Steps executed: `{len(result.steps)}`",
    ]

    if result.completion_flag is not None:
        lines.append(f"- Completion flag: `{result.completion_flag}`")

    if result.terminal_error is not None:
        lines.append(f"- Terminal error: `{result.terminal_error}`")

    lines.extend(
        [
            "",
            "## Step Summary",
            "",
            "| Step | Action | HTTP status | Attempts |",
            "|---|---|---|---|",
        ]
    )

    for step_index, step in enumerate(result.steps, start=1):
        lines.append(
            f"| {step_index} | `{step.action}` | `{step.response.http_status}` | `{step.response.attempts_used}` |"
        )

    return "\n".join(lines) + "\n"


# Mask secret fields before request payloads are written to disk.
def mask_payload_for_storage(payload: dict[str, Any]) -> dict[str, Any]:
    masked_payload = dict(payload)
    if "apikey" in masked_payload:
        masked_payload["apikey"] = REDACTED

    return masked_payload


# Write JSONL records to one output file with stable UTF-8 formatting.
def write_jsonl_file(file_path: Path, records: list[dict[str, Any]]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(record, ensure_ascii=False) for record in records]
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# Return one timezone-aware timestamp string for saved artifacts.
def current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
