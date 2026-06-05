# Deterministic candidate extraction from fetched mailbox messages.

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from src.apps.L9_mailbox.validator import (
    MailboxAnswer,
    is_valid_confirmation_code,
    is_valid_date,
    is_valid_password,
    validate_mailbox_answer,
)


DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
CONFIRMATION_CODE_PATTERN = re.compile(r"\bSEC-[A-Za-z0-9]{32}\b")
PASSWORD_PATTERNS = (
    re.compile(r"\bpassword\s*[:=]\s*([^\s,;]+)", re.IGNORECASE),
    re.compile(r"\bpass\s*[:=]\s*([^\s,;]+)", re.IGNORECASE),
    re.compile(r"\bhaslo\s*[:=]\s*([^\s,;]+)", re.IGNORECASE),
    re.compile(r"\bhas\u0142o\s*[:=]\s*([^\s,;]+)", re.IGNORECASE),
)
TEXT_FIELDS = (
    "body",
    "text",
    "content",
    "message",
    "html",
    "subject",
    "snippet",
)
ID_FIELDS = ("messageID", "messageId", "message_id", "rowID", "rowId", "row_id", "id")


# Store one extracted field candidate with traceable evidence.
@dataclass(frozen=True)
class ExtractedCandidate:
    field: str
    value: str
    message_id: int | str | None
    reason: str


# Store structured extraction output for later validation and synthesis.
@dataclass(frozen=True)
class ExtractionResult:
    candidates: tuple[ExtractedCandidate, ...]
    proposed_answer: MailboxAnswer
    validation_errors: tuple[str, ...]
    uncertainties: tuple[str, ...]


# Read one possible identifier from a message object.
def get_message_identifier(message: Mapping[str, Any]) -> int | str | None:
    for field_name in ID_FIELDS:
        value = message.get(field_name)
        if isinstance(value, (int, str)):
            return value

    return None


# Collect searchable message text while tolerating API field-name variants.
def collect_message_text(message: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for field_name in TEXT_FIELDS:
        value = message.get(field_name)
        if isinstance(value, str):
            parts.append(value)

    return "\n".join(parts)


# Normalize unknown getMessages payload shapes into message dictionaries.
def extract_message_records(payload: Any) -> list[Mapping[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, Mapping)]

    if not isinstance(payload, Mapping):
        return []

    for field_name in ("messages", "results", "items", "data"):
        value = payload.get(field_name)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]

    return [payload]


# Extract all syntactic candidates from one fetched message body.
def extract_candidates_from_message(message: Mapping[str, Any]) -> tuple[ExtractedCandidate, ...]:
    message_id = get_message_identifier(message)
    text = collect_message_text(message)
    candidates: list[ExtractedCandidate] = []

    for match in DATE_PATTERN.finditer(text):
        value = match.group(0)
        if is_valid_date(value):
            candidates.append(
                ExtractedCandidate(
                    field="date",
                    value=value,
                    message_id=message_id,
                    reason="valid YYYY-MM-DD date found in message text",
                )
            )

    for match in CONFIRMATION_CODE_PATTERN.finditer(text):
        value = match.group(0)
        if is_valid_confirmation_code(value):
            candidates.append(
                ExtractedCandidate(
                    field="confirmation_code",
                    value=value,
                    message_id=message_id,
                    reason="SEC confirmation code pattern found in message text",
                )
            )

    for pattern in PASSWORD_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1).strip()
            if is_valid_password(value):
                candidates.append(
                    ExtractedCandidate(
                        field="password",
                        value=value,
                        message_id=message_id,
                        reason="password-like label found in message text",
                    )
                )

    return tuple(candidates)


# Pick the first candidate for each required field and keep ambiguity visible.
def build_proposed_answer(candidates: Sequence[ExtractedCandidate]) -> tuple[MailboxAnswer, tuple[str, ...]]:
    values_by_field: dict[str, list[ExtractedCandidate]] = {
        "password": [],
        "date": [],
        "confirmation_code": [],
    }

    for candidate in candidates:
        if candidate.field in values_by_field:
            values_by_field[candidate.field].append(candidate)

    uncertainties: list[str] = []
    for field_name, field_candidates in values_by_field.items():
        unique_values = {candidate.value for candidate in field_candidates}
        if not field_candidates:
            uncertainties.append(f"{field_name} was not found")
        elif len(unique_values) > 1:
            uncertainties.append(f"{field_name} has multiple candidate values")

    return (
        MailboxAnswer(
            password=values_by_field["password"][0].value if values_by_field["password"] else None,
            date=values_by_field["date"][0].value if values_by_field["date"] else None,
            confirmation_code=(
                values_by_field["confirmation_code"][0].value
                if values_by_field["confirmation_code"]
                else None
            ),
        ),
        tuple(uncertainties),
    )


# Extract structured candidates from fetched message payloads.
def extract_from_messages_payload(payload: Any) -> ExtractionResult:
    messages = extract_message_records(payload)
    candidates: list[ExtractedCandidate] = []

    for message in messages:
        candidates.extend(extract_candidates_from_message(message))

    proposed_answer, uncertainties = build_proposed_answer(candidates)
    validation_result = validate_mailbox_answer(proposed_answer)

    return ExtractionResult(
        candidates=tuple(candidates),
        proposed_answer=proposed_answer,
        validation_errors=validation_result.errors,
        uncertainties=uncertainties,
    )


# Build a full local extraction report for ignored runtime data and debugging.
def build_extraction_report(result: ExtractionResult) -> dict[str, Any]:
    return {
        "candidate_count": len(result.candidates),
        "candidates": [
            {
                "field": candidate.field,
                "value": candidate.value,
                "message_id": candidate.message_id,
                "reason": candidate.reason,
            }
            for candidate in result.candidates
        ],
        "proposed_answer": {
            "password": result.proposed_answer.password,
            "date": result.proposed_answer.date,
            "confirmation_code": result.proposed_answer.confirmation_code,
        },
        "validation_errors": list(result.validation_errors),
        "uncertainties": list(result.uncertainties),
    }


# Build a reduced extraction report for places that should not contain candidate values.
def build_masked_extraction_report(result: ExtractionResult) -> dict[str, Any]:
    return {
        "candidate_count": len(result.candidates),
        "candidates": [
            {
                "field": candidate.field,
                "has_value": bool(candidate.value),
                "message_id": candidate.message_id,
                "reason": candidate.reason,
            }
            for candidate in result.candidates
        ],
        "proposed_answer": {
            "has_password": result.proposed_answer.password is not None,
            "has_date": result.proposed_answer.date is not None,
            "has_confirmation_code": result.proposed_answer.confirmation_code is not None,
        },
        "validation_errors": list(result.validation_errors),
        "uncertainties": list(result.uncertainties),
    }


# Build an explicit human-debug view with candidate values and a warning banner.
def build_debug_extraction_view(result: ExtractionResult) -> dict[str, Any]:
    debug_view = build_extraction_report(result)
    debug_view["storage_warning"] = (
        "Debug view may contain course API feedback and candidate values. "
        "It may be written to ignored runtime data for debugging. Do not commit "
        "or publish it. Never store API keys, operational endpoints, or external "
        "access credentials outside .env."
    )
    return debug_view
