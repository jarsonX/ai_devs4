# Guarded Hub verification client for the L11 evaluation workflow.

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import requests

from src.apps.L11_evaluation.config import HubConfig
from src.apps.L11_evaluation.models import EvaluationAnswer


REDACTED = "***REDACTED***"
FLAG_PATTERN = re.compile(r"\{FLG:[^}]+}")


# Preserve one Hub response in a stable shape for workflow code and ignored runtime logs.
@dataclass(frozen=True)
class HubResponse:
    status_code: int
    payload: Any
    text: str


# Build the exact verification payload expected by the evaluation Hub task.
def build_verify_payload(
    config: HubConfig,
    answer: EvaluationAnswer,
) -> dict[str, Any]:
    return {
        "apikey": config.api_key,
        "task": config.task_name,
        "answer": {
            "recheck": answer.recheck,
        },
    }


# Mask the API key before request payloads are written to logs or reports.
def mask_payload_for_storage(payload: dict[str, Any]) -> dict[str, Any]:
    masked_payload = dict(payload)
    if "apikey" in masked_payload:
        masked_payload["apikey"] = REDACTED
    return masked_payload


# Convert one HTTP response into a stable object for local handling.
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


# Detect whether a Hub response contains a course flag.
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


# Convert a Hub response into a runtime-log payload with full Hub feedback.
def hub_response_for_log(response: HubResponse) -> dict[str, Any]:
    return {
        "status_code": response.status_code,
        "payload": response.payload,
        "text": response.text,
        "flag_found": bool(extract_flag(response.payload) or extract_flag(response.text)),
    }


# Keep Hub verification attempts bounded before any external request is sent.
class VerifyRequestGuard:
    # Store a strict request cap for the current evaluation run.
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


# Submit guarded verification requests to the configured Hub endpoint.
class HubClient:
    # Store Hub config plus an injectable HTTP session for local tests.
    def __init__(
        self,
        config: HubConfig,
        *,
        session: requests.Session | Any | None = None,
        timeout_seconds: int = 30,
        guard: VerifyRequestGuard | None = None,
    ) -> None:
        self.config = config
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds
        self.guard = guard or VerifyRequestGuard(max_requests=1)

    # Submit one final answer payload and return masked request data plus raw Hub feedback.
    def verify_answer(self, answer: EvaluationAnswer) -> tuple[dict[str, Any], HubResponse]:
        self.guard.consume()
        payload = build_verify_payload(self.config, answer)
        response = self.session.post(
            self.config.verify_url,
            json=payload,
            timeout=self.timeout_seconds,
        )
        return mask_payload_for_storage(payload), build_hub_response(response)
