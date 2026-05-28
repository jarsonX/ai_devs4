# Hub verification client for the L8 failure exercise.

from __future__ import annotations

import re
from typing import Any

import requests

from src.apps.L8_failure.config import HubConfig
from src.apps.L8_failure.models import HubResponse


REQUEST_TIMEOUT_SECONDS = 30
REDACTED = "***REDACTED***"
FLAG_PATTERN = re.compile(r"\{FLG:[^}]+}")


# Build the payload expected by the Hub failure verifier.
def build_verify_payload(config: HubConfig, logs: str) -> dict[str, Any]:
    return {
        "apikey": config.api_key,
        "task": config.task_name,
        "answer": {
            "logs": logs,
        },
    }


# Mask API keys before request data is written to reports.
def mask_payload_for_storage(payload: dict[str, Any]) -> dict[str, Any]:
    masked_payload = dict(payload)
    masked_payload["apikey"] = REDACTED
    return masked_payload


# Convert a requests response into stable report-friendly data.
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


# Extract a course flag from nested response data when the Hub succeeds.
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


# Track Hub verification attempts so feedback loops stay bounded.
class VerifyRequestGuard:
    # Store a strict maximum before any external verification call can run.
    def __init__(self, max_requests: int) -> None:
        self.max_requests = max_requests
        self.used_requests = 0

    # Count one planned verification request and fail before the Hub call when capped.
    def consume(self) -> None:
        if self.used_requests >= self.max_requests:
            raise RuntimeError(
                f"Hub verification guard reached {self.max_requests} calls."
            )
        self.used_requests += 1


# Submit guarded verification requests to the configured Hub endpoint.
class HubClient:
    # Store Hub config plus injectable HTTP session for tests.
    def __init__(
        self,
        config: HubConfig,
        *,
        session: requests.Session | None = None,
        timeout_seconds: int = REQUEST_TIMEOUT_SECONDS,
        guard: VerifyRequestGuard | None = None,
    ) -> None:
        self.config = config
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds
        self.guard = guard or VerifyRequestGuard(max_requests=1)

    # Submit one condensed log answer and preserve raw Hub feedback.
    def verify_logs(self, logs: str) -> HubResponse:
        self.guard.consume()
        response = self.session.post(
            self.config.verify_url,
            json=build_verify_payload(self.config, logs),
            timeout=self.timeout_seconds,
        )
        return build_hub_response(response)
