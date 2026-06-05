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
    re.compile(r"\bhas\u0142em\s*[:=]\s*([^\s,;]+)", re.IGNORECASE),
    re.compile(r"\bhaslem\s*[:=]\s*([^\s,;]+)", re.IGNORECASE),
)
PASSWORD_LABEL_PATTERN = re.compile(
    r"\b(password|pass|haslo|has\u0142o|haslem|has\u0142em)\b",
    re.IGNORECASE,
)
CONFIRMATION_CORRECTION_PATTERN = re.compile(
    r"\b(poprawny|correct|corrected|fixed|zly|z\u0142y|wrong)\b",
    re.IGNORECASE,
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
    priority: int = 0


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


# Extract password candidates that appear on the next non-empty line after a password label.
def extract_multiline_password_candidates(
    text: str,
    *,
    message_id: int | str | None,
) -> list[ExtractedCandidate]:
    candidates: list[ExtractedCandidate] = []
    lines = text.splitlines()

    for index, line in enumerate(lines):
        if not PASSWORD_LABEL_PATTERN.search(line):
            continue

        stripped_line = line.strip()
        if ":" not in stripped_line and "=" not in stripped_line:
            continue

        for next_index in range(index + 1, len(lines)):
            next_line = lines[next_index].strip()
            if not next_line:
                continue

            value = next_line.split()[0].strip(",;")
            if is_valid_password(value):
                candidates.append(
                    ExtractedCandidate(
                        field="password",
                        value=value,
                        message_id=message_id,
                        reason="password value found on the next line after a password label",
                        priority=10,
                    )
                )
            break

    return candidates


# Score confirmation-code candidates so corrected codes beat earlier incorrect variants.
def get_confirmation_code_priority(text: str, match_start: int, match_end: int) -> int:
    local_context = text[max(0, match_start - 60) : min(len(text), match_end + 60)]
    if CONFIRMATION_CORRECTION_PATTERN.search(local_context):
        if re.search(r"\b(poprawny|correct|corrected|fixed)\b", local_context, re.IGNORECASE):
            return 10
        if re.search(r"\b(zly|z\u0142y|wrong)\b", local_context, re.IGNORECASE):
            return -5
    return 0


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
                    priority=0,
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
                    priority=get_confirmation_code_priority(text, match.start(), match.end()),
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
                        priority=5,
                    )
                )

    candidates.extend(
        extract_multiline_password_candidates(
            text,
            message_id=message_id,
        )
    )

    return tuple(candidates)


# Pick the best candidate for one field using explicit priority, then stable appearance order.
def select_best_candidate(field_candidates: Sequence[ExtractedCandidate]) -> ExtractedCandidate | None:
    if not field_candidates:
        return None
    return max(
        enumerate(field_candidates),
        key=lambda item: (item[1].priority, -item[0]),
    )[1]


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

    best_password = select_best_candidate(values_by_field["password"])
    best_date = select_best_candidate(values_by_field["date"])
    best_confirmation_code = select_best_candidate(values_by_field["confirmation_code"])

    return (
        MailboxAnswer(
            password=best_password.value if best_password else None,
            date=best_date.value if best_date else None,
            confirmation_code=best_confirmation_code.value if best_confirmation_code else None,
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
                "priority": candidate.priority,
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
                "priority": candidate.priority,
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
