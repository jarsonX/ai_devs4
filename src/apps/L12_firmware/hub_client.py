# Guarded HTTP client for submitting the firmware confirmation code.

from __future__ import annotations

from typing import Any

import requests

from src.apps.L12_firmware.config import (
    ExternalApiConfig,
    MAX_SUBMIT_REQUESTS,
    REQUEST_TIMEOUT_SECONDS,
)
from src.apps.L12_firmware.http_client import ApiResponse, RequestGuard, post_json


REDACTED = "***REDACTED***"


# Build the exact verification payload expected by the firmware task.
def build_verify_payload(
    config: ExternalApiConfig,
    confirmation: str,
) -> dict[str, Any]:
    return {
        "apikey": config.api_key,
        "task": config.task_name,
        "answer": {
            "confirmation": confirmation,
        },
    }


# Mask the API key before verification payloads are stored in runtime reports.
def mask_verify_payload(payload: dict[str, Any]) -> dict[str, Any]:
    masked_payload = dict(payload)
    if "apikey" in masked_payload:
        masked_payload["apikey"] = REDACTED
    return masked_payload


# Submit one bounded firmware answer to the course Hub.
class HubClient:
    # Store Hub configuration, an injectable session, and its request guard.
    def __init__(
        self,
        config: ExternalApiConfig,
        *,
        session: requests.Session | Any | None = None,
        timeout_seconds: int = REQUEST_TIMEOUT_SECONDS,
        guard: RequestGuard | None = None,
    ) -> None:
        self.config = config
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds
        self.guard = guard or RequestGuard(MAX_SUBMIT_REQUESTS)

    # Submit one confirmation after later workflow layers validate its provenance.
    def submit_confirmation(
        self,
        confirmation: str,
    ) -> tuple[dict[str, Any], ApiResponse]:
        payload = build_verify_payload(self.config, confirmation)
        response = post_json(
            session=self.session,
            url=self.config.verify_url,
            payload=payload,
            timeout_seconds=self.timeout_seconds,
            guard=self.guard,
        )
        return mask_verify_payload(payload), response
