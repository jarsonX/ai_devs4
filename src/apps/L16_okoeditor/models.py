# Typed workflow models for the L16 okoeditor app.

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


# Store one record discovered on a list page.
@dataclass(frozen=True)
class RecordLink:
    page: str
    record_id: str
    url: str
    title: str
    preview: str
    anchor_text: str


# Store one normalized record detail page.
@dataclass(frozen=True)
class RecordDetail:
    page: str
    record_id: str
    url: str
    title: str
    code: str | None
    title_without_code: str
    visible_text: str
    body_text: str
    status_label: str | None = None
    is_done: bool | None = None


# Store the current OKO state needed for deterministic planning.
@dataclass(frozen=True)
class OkoState:
    incident_links: tuple[RecordLink, ...]
    task_links: tuple[RecordLink, ...]
    incident_details: tuple[RecordDetail, ...]
    task_details: tuple[RecordDetail, ...]


# Store the three grounded targets needed by the task.
@dataclass(frozen=True)
class TargetSelection:
    skolwin_incident: RecordDetail
    skolwin_task: RecordDetail
    komarowo_candidate: RecordDetail


# Store one prepared API mutation plus its deterministic verification hints.
@dataclass(frozen=True)
class UpdateInstruction:
    page: str
    record_id: str
    reason: str
    title: str | None = None
    content: str | None = None
    done: str | None = None
    expected_title_substrings: tuple[str, ...] = ()
    expected_body_substrings: tuple[str, ...] = ()
    expected_done: bool | None = None


# Store one HTTP response in a normalized form.
@dataclass(frozen=True)
class VerifyResponse:
    status_code: int
    payload: Any | None
    text: str


# Preserve the final workflow status for callers and tests.
@dataclass(frozen=True)
class WorkflowResult:
    status: str
    reason: str
    apply_mode: bool
    planned_update_count: int
    run_log_path: str
    plan_report_path: str
    final_response_path: str | None = None
    flag_found: bool = False


# Return one copy of the record without the full visible page dump.
def redact_record_for_reports(record: RecordDetail) -> dict[str, Any]:
    return {
        "page": record.page,
        "record_id": record.record_id,
        "url": record.url,
        "title": record.title,
        "code": record.code,
        "title_without_code": record.title_without_code,
        "body_text": record.body_text,
        "status_label": record.status_label,
        "is_done": record.is_done,
    }


# Convert one dataclass tree into a JSON-safe dictionary.
def dataclass_to_dict(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {
            key: dataclass_to_dict(nested)
            for key, nested in asdict(value).items()
        }
    if isinstance(value, tuple):
        return [dataclass_to_dict(item) for item in value]
    if isinstance(value, list):
        return [dataclass_to_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: dataclass_to_dict(nested) for key, nested in value.items()}
    return value
