# This module submits guarded mailbox answers to the course verification Hub.

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import requests

from src.apps.L9_mailbox.config import ExternalApiConfig
from src.apps.L9_mailbox.validator import MailboxAnswer


REQUEST_TIMEOUT_SECONDS = 30
REDACTED = "***REDACTED***"
FLAG_PATTERN = re.compile(r"\{FLG:[^}]+}")


# Preserve one Hub response in a stable shape for reports and retry logic.
@dataclass(frozen=True)
class HubResponse:
    status_code: int
    payload: Any
    text: str


# Build the exact verification payload expected by the mailbox Hub task.
def build_verify_payload(
    config: ExternalApiConfig,
    answer: MailboxAnswer,
) -> dict[str, Any]:
    return {
        "apikey": config.api_key,
        "task": config.task_name,
        "answer": {
            "date": answer.date,
            "password": answer.password,
            "confirmation_code": answer.confirmation_code,
        },
    }


# Mask the API key before request payloads are written to reports.
def mask_payload_for_storage(payload: dict[str, Any]) -> dict[str, Any]:
    masked_payload = dict(payload)
    if "apikey" in masked_payload:
        masked_payload["apikey"] = REDACTED
    return masked_payload


# Convert one HTTP response into a report-friendly Hub response object.
def build_hub_response(response: requests.Response) -> HubResponse:
    try:
        payload = response.json()
    except requests.JSONDecodeError:
        payload = None

    return HubResponse(
        status_code=response.status_code,
        payload=payload,
        text=response.text,
    )


# Extract a course flag from nested Hub feedback when verification succeeds.
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


# Keep Hub submit attempts bounded before any external request is sent.
class SubmitRequestGuard:
    # Store a strict request cap for the current mailbox workbench run.
    def __init__(self, max_requests: int) -> None:
        self.max_requests = max_requests
        self.used_requests = 0

    # Count one planned request and stop before the Hub call when capped.
    def consume(self) -> None:
        if self.used_requests >= self.max_requests:
            raise RuntimeError(
                f"Hub submission guard reached {self.max_requests} calls."
            )
        self.used_requests += 1


# Submit guarded mailbox verification requests to the configured Hub endpoint.
class HubClient:
    # Store Hub config plus an injectable HTTP session for local tests.
    def __init__(
        self,
        config: ExternalApiConfig,
        *,
        session: requests.Session | None = None,
        timeout_seconds: int = REQUEST_TIMEOUT_SECONDS,
        guard: SubmitRequestGuard | None = None,
    ) -> None:
        self.config = config
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds
        self.guard = guard or SubmitRequestGuard(max_requests=1)

    # Submit one mailbox answer and preserve raw Hub feedback for retries.
    def verify_answer(self, answer: MailboxAnswer) -> HubResponse:
        self.guard.consume()
        response = self.session.post(
            self.config.verify_url,
            json=build_verify_payload(self.config, answer),
            timeout=self.timeout_seconds,
        )
        return build_hub_response(response)
