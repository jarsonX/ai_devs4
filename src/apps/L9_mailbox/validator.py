# Deterministic validation for mailbox answer candidates.

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime


CONFIRMATION_CODE_PATTERN = re.compile(r"^SEC-[A-Za-z0-9]{32}$")
DATE_FORMAT = "%Y-%m-%d"


# Store the three fields required by the mailbox verification endpoint.
@dataclass(frozen=True)
class MailboxAnswer:
    password: str | None
    date: str | None
    confirmation_code: str | None


# Return validation status together with concrete errors for debugging.
@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    errors: tuple[str, ...]


# Check that a candidate date is an actual calendar date in YYYY-MM-DD form.
def is_valid_date(value: str | None) -> bool:
    if value is None:
        return False

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False

    try:
        parsed_date = datetime.strptime(value, DATE_FORMAT)
    except ValueError:
        return False

    return parsed_date.strftime(DATE_FORMAT) == value


# Check that a password candidate contains non-whitespace content.
def is_valid_password(value: str | None) -> bool:
    return isinstance(value, str) and bool(value.strip())


# Check the SEC-prefixed confirmation code shape required by the exercise.
def is_valid_confirmation_code(value: str | None) -> bool:
    return isinstance(value, str) and bool(CONFIRMATION_CODE_PATTERN.fullmatch(value))


# Validate a full answer candidate before any Hub submission can happen.
def validate_mailbox_answer(answer: MailboxAnswer) -> ValidationResult:
    errors: list[str] = []

    if not is_valid_password(answer.password):
        errors.append("password must be a non-empty string")

    if not is_valid_date(answer.date):
        errors.append("date must be a real calendar date in YYYY-MM-DD format")

    if not is_valid_confirmation_code(answer.confirmation_code):
        errors.append("confirmation_code must match SEC- followed by 32 alphanumeric characters")

    return ValidationResult(
        is_valid=not errors,
        errors=tuple(errors),
    )
