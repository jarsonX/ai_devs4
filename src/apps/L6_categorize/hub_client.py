# HTTP client helpers for the L6 categorize Hub workflow.

from __future__ import annotations

from typing import Any

import requests

from src.apps.L6_categorize.config import HubConfig
from src.apps.L6_categorize.models import HubResponse


REQUEST_TIMEOUT_SECONDS = 30
REDACTED = "***REDACTED***"


# Build the exact payload expected by the Hub categorize verifier.
def build_verify_payload(config: HubConfig, prompt: str) -> dict[str, Any]:
    return {
        "apikey": config.api_key,
        "task": config.task_name,
        "answer": {
            "prompt": prompt,
        },
    }


# Mask secret fields before writing request payloads to reports.
def mask_payload_for_storage(payload: dict[str, Any]) -> dict[str, Any]:
    masked_payload = dict(payload)
    masked_payload["apikey"] = REDACTED
    return masked_payload


# Convert an HTTP response into a small object that preserves JSON and raw text.
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


# Communicate with the Hub endpoints required by the categorize workflow.
class HubClient:
    # Store Hub configuration and an injectable HTTP session.
    def __init__(
        self,
        config: HubConfig,
        session: requests.Session | None = None,
        timeout_seconds: int = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self.config = config
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds

    # Download the latest CSV body from the configured Hub data URL.
    def download_csv(self) -> HubResponse:
        response = self.session.get(
            self.config.data_url,
            timeout=self.timeout_seconds,
        )
        return build_hub_response(response)

    # Download the latest CSV body and fail on HTTP errors.
    def download_csv_text(self) -> str:
        csv_response = self.download_csv()
        if csv_response.status_code >= 400:
            raise RuntimeError(f"CSV download failed with HTTP {csv_response.status_code}.")

        return csv_response.text

    # Submit one prompt to the Hub verifier and preserve the raw response.
    def verify_prompt(self, prompt: str) -> HubResponse:
        response = self.session.post(
            self.config.verify_url,
            json=build_verify_payload(self.config, prompt),
            timeout=self.timeout_seconds,
        )
        return build_hub_response(response)

    # Reset the Hub budget by sending the special reset prompt.
    def reset_budget(self) -> HubResponse:
        return self.verify_prompt("reset")
