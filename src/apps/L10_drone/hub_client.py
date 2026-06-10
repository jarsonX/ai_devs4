# Hub verification client for the L10 drone exercise.

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import requests

from src.apps.L10_drone.config import HubConfig


REDACTED = "***REDACTED***"
FLAG_PATTERN = re.compile(r"\{FLG:[^}]+}")


# Preserve one Hub response in a stable shape for workflow and logs.
@dataclass(frozen=True)
class HubResponse:
    status_code: int
    payload: Any
    text: str


# Build the exact verification payload expected by the drone Hub task.
def build_verify_payload(
    config: HubConfig,
    instructions: list[str],
) -> dict[str, Any]:
    return {
        "apikey": config.api_key,
        "task": config.task_name,
        "answer": {
            "instructions": instructions,
        },
    }


# Mask the API key before request payloads are written to logs.
def mask_payload_for_storage(payload: dict[str, Any]) -> dict[str, Any]:
    masked_payload = dict(payload)
    if "apikey" in masked_payload:
        masked_payload["apikey"] = REDACTED
    return masked_payload


# Convert one HTTP response into a log-friendly Hub response object.
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


# Redact course flags before Hub feedback is written to logs.
def redact_flags(value: Any) -> Any:
    if isinstance(value, str):
        return FLAG_PATTERN.sub("***REDACTED_FLAG***", value)
    if isinstance(value, dict):
        return {key: redact_flags(nested_value) for key, nested_value in value.items()}
    if isinstance(value, list):
        return [redact_flags(nested_value) for nested_value in value]
    return value


# Keep Hub verification attempts bounded before any external request is sent.
class VerifyRequestGuard:
    # Store a strict request cap for the current drone run.
    def __init__(self, max_requests: int) -> None:
        self.max_requests = max_requests
        self.used_requests = 0

    # Count one planned request and stop before the Hub call when capped.
    def consume(self) -> None:
        if self.used_requests >= self.max_requests:
            raise RuntimeError(
                f"Hub verification guard reached {self.max_requests} calls."
            )
        self.used_requests += 1


# Submit guarded drone verification requests to the configured Hub endpoint.
class HubClient:
    # Store Hub config plus an injectable HTTP session for local tests.
    def __init__(
        self,
        config: HubConfig,
        *,
        session: requests.Session | None = None,
        timeout_seconds: int = 30,
        guard: VerifyRequestGuard | None = None,
    ) -> None:
        self.config = config
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds
        self.guard = guard or VerifyRequestGuard(max_requests=1)

    # Submit one instruction list and preserve raw Hub feedback for repair.
    def verify_instructions(self, instructions: list[str]) -> tuple[dict[str, Any], HubResponse]:
        self.guard.consume()
        payload = build_verify_payload(self.config, instructions)
        response = self.session.post(
            self.config.verify_url,
            json=payload,
            timeout=self.timeout_seconds,
        )
        return mask_payload_for_storage(payload), build_hub_response(response)


# Convert a Hub response into a JSON-safe log payload.
def hub_response_for_log(response: HubResponse) -> dict[str, Any]:
    flag_found = bool(extract_flag(response.payload) or extract_flag(response.text))
    return {
        "status_code": response.status_code,
        "payload": redact_flags(response.payload),
        "text": redact_flags(response.text),
        "flag_found": flag_found,
    }
