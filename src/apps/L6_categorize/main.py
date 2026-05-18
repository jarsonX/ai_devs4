# CLI workflow for the L6 categorize exercise runner.

from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.apps.L6_categorize.config import (
    AppConfig,
    ensure_runtime_directories,
    load_app_config,
)
from src.apps.L6_categorize.csv_loader import parse_goods_items
from src.apps.L6_categorize.hub_client import (
    HubClient,
    build_verify_payload,
    mask_payload_for_storage,
)
from src.apps.L6_categorize.models import (
    GoodsItem,
    HubResponse,
    ItemVerification,
    RunLogEntry,
    RunReport,
)
from src.apps.L6_categorize.prompt_builder import build_item_prompt


FLAG_PATTERN = re.compile(r"\{FLG:[^}]+}")
EXPECTED_ITEM_COUNT = 10
HUB_FAILURE_HINTS = ("error", "failed", "incorrect", "wrong", "budget")


# Report-only: timestamps make the JSON report readable as an execution log.
# Return the current UTC time as a stable report timestamp.
def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# Report-only: every significant workflow action is stored as one event.
# Build one timestamped report event.
def make_event(
    step: str,
    message: str,
    request: dict[str, Any] | None = None,
    response: HubResponse | None = None,
    item: GoodsItem | None = None,
    details: dict[str, Any] | None = None,
) -> RunLogEntry:
    return RunLogEntry(
        timestamp=utc_now_iso(),
        step=step,
        message=message,
        request=request,
        response=response,
        item=item,
        details=details or {},
    )


# Detect whether a Hub response should stop the current attempt.
def is_hub_failure(response: HubResponse) -> bool:
    if response.status_code >= 400:
        return True

    if isinstance(response.payload, dict):
        message = str(response.payload.get("message", "")).lower()
        if any(hint in message for hint in HUB_FAILURE_HINTS):
            return True

    return False


# Extract a course flag from any text-like value in a response.
def extract_flag(value: Any) -> str | None:
    if isinstance(value, str):
        match = FLAG_PATTERN.search(value)
        return match.group(0) if match else None

    if isinstance(value, dict):
        for nested_value in value.values():
            flag = extract_flag(nested_value)
            if flag:
                return flag

    if isinstance(value, list):
        for nested_value in value:
            flag = extract_flag(nested_value)
            if flag:
                return flag

    return None


# Report-only: dataclasses need conversion before JSON serialization.
# Convert a run report into JSON-serializable data.
def report_to_dict(report: RunReport) -> dict[str, Any]:
    return asdict(report)


# Report-only: the report is intentionally pretty-printed for manual reading.
# Persist the run report as pretty JSON for step-by-step inspection.
def save_run_report(report: RunReport, report_file: Path) -> None:
    report_file.write_text(
        json.dumps(report_to_dict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# Add the reset request and response to the report.
def run_reset_step(config: AppConfig, client: HubClient, report: RunReport) -> bool:
    # Report log: store the outgoing reset payload without the secret API key.
    request_payload = mask_payload_for_storage(
        build_verify_payload(config.hub, "reset"),
    )
    response = client.reset_budget()
    # Report log: record both the reset request and the exact Hub response.
    report.events.append(
        make_event(
            step="reset_budget",
            message="Sent reset prompt to start from a clean budget state.",
            request=request_payload,
            response=response,
        )
    )

    if is_hub_failure(response):
        report.error_summary = "Reset request failed."
        return False

    return True


# Download the latest CSV, save it locally, and parse goods items.
def run_csv_steps(config: AppConfig, client: HubClient, report: RunReport) -> list[GoodsItem]:
    csv_response = client.download_csv()
    # Report log: record the download result, but keep the secret-bearing URL out.
    report.events.append(
        make_event(
            step="download_csv",
            message="Downloaded latest categorize CSV from configured data URL.",
            request={"method": "GET", "url_config": "HUB_DATA_URL"},
            response=csv_response,
            details={"characters": len(csv_response.text)},
        )
    )

    if is_hub_failure(csv_response):
        raise RuntimeError(f"CSV download failed with HTTP {csv_response.status_code}.")

    config.paths.latest_csv_file.write_text(csv_response.text, encoding="utf-8")
    # Report log: record where the downloaded CSV was stored.
    report.events.append(
        make_event(
            step="save_csv",
            message="Saved downloaded CSV to the app data directory.",
            details={"path": str(config.paths.latest_csv_file.relative_to(config.paths.repo_root))},
        )
    )

    items = parse_goods_items(csv_response.text)
    # Report log: keep the parsed item count visible before verification starts.
    report.items_count = len(items)
    report.events.append(
        make_event(
            step="parse_csv",
            message="Parsed goods items from CSV.",
            details={"items_count": len(items)},
        )
    )

    if len(items) != EXPECTED_ITEM_COUNT:
        raise ValueError(f"Expected {EXPECTED_ITEM_COUNT} goods items, got {len(items)}.")

    return items


# Submit one verification request per item and record every Hub response.
def run_verification_steps(
    config: AppConfig,
    client: HubClient,
    report: RunReport,
    items: list[GoodsItem],
) -> None:
    for item in items:
        prompt = build_item_prompt(item)
        # Report log: store the exact prompt sent to the Hub, with apikey masked.
        request_payload = mask_payload_for_storage(
            build_verify_payload(config.hub, prompt),
        )
        response = client.verify_prompt(prompt)

        # Report log: keep both a compact verification list and chronological event.
        report.verifications.append(
            ItemVerification(item=item, prompt=prompt, response=response)
        )
        report.events.append(
            make_event(
                step="verify_item",
                message="Submitted one item prompt to the Hub verifier.",
                request=request_payload,
                response=response,
                item=item,
            )
        )

        flag = extract_flag(response.payload) or extract_flag(response.text)
        if flag:
            report.flag = flag
            report.success = True
            return

        if is_hub_failure(response):
            report.error_summary = f"Hub verification failed for item {item.item_id}."
            return

    report.error_summary = "All items were submitted, but no flag was returned."


# Run the complete categorize attempt and fill the report.
def run_workflow(config: AppConfig, client: HubClient, report: RunReport) -> None:
    if not run_reset_step(config, client, report):
        return

    items = run_csv_steps(config, client, report)
    run_verification_steps(config, client, report, items)


# CLI entrypoint for the L6 categorize runner.
def main() -> int:
    config = load_app_config()
    ensure_runtime_directories(config.paths)

    # Report log: the report object is passed through the workflow and filled in place.
    report = RunReport(started_at=utc_now_iso())
    exit_code = 0

    try:
        run_workflow(config, HubClient(config.hub), report)
        if not report.success:
            exit_code = 1
    except Exception as error:
        # Report log: preserve unexpected runtime failures in the same event stream.
        report.error_summary = str(error)
        report.events.append(
            make_event(
                step="runtime_error",
                message="Workflow stopped because an unexpected error occurred.",
                details={
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
            )
        )
        exit_code = 1
    finally:
        # Report log: always write the report, even when the workflow fails.
        report.ended_at = utc_now_iso()
        save_run_report(report, config.paths.run_report_file)

    print(f"Run report saved to {config.paths.run_report_file}")
    if report.flag:
        print(report.flag)
    elif report.error_summary:
        print(report.error_summary)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
