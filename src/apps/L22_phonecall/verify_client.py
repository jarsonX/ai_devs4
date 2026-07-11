# Guarded HTTP client for the L22 phonecall Hub API.

from __future__ import annotations

from typing import Any, Protocol

import requests

from src.apps.L22_phonecall.config import HubConfig
from src.apps.L22_phonecall.models import ApiResponse, LoggedExchange
from src.apps.L22_phonecall.run_log import mask_secret_fields


# Define the small subset of requests.Session used by the client.
class SessionProtocol(Protocol):
    # Send one POST request through an injected HTTP session.
    def post(self, *args: Any, **kwargs: Any) -> requests.Response:
        ...


# Read a JSON response when possible while keeping text fallback.
def build_api_response(response: requests.Response) -> ApiResponse:
    try:
        payload = response.json()
    except ValueError:
        payload = None
    return ApiResponse(
        status_code=response.status_code,
        payload=payload,
        text=response.text,
    )


# Build the exact Hub verify payload for one answer object.
def build_verify_payload(config: HubConfig, answer: dict[str, Any]) -> dict[str, Any]:
    return {
        "apikey": config.api_key,
        "task": config.task_name,
        "answer": answer,
    }


# Send phonecall task actions through one guarded HTTP session.
class PhonecallVerifyClient:
    # Store Hub config plus timeout and request-count guard.
    def __init__(
        self,
        config: HubConfig,
        *,
        timeout_seconds: int,
        max_requests: int,
        session: SessionProtocol | None = None,
    ) -> None:
        if max_requests < 1:
            raise ValueError("max_requests must be >= 1.")
        self.hub_config = config
        self.timeout_seconds = timeout_seconds
        self.max_requests = max_requests
        self.session = session or requests.Session()
        self._request_count = 0

    # Return how many Hub requests have been used in this run.
    def request_count(self) -> int:
        return self._request_count

    # Send one answer object to the Hub after checking the request guard.
    def call(self, answer: dict[str, Any], *, action: str) -> LoggedExchange:
        self._request_count += 1
        if self._request_count > self.max_requests:
            raise ValueError("The Hub request guard was exceeded.")

        payload = build_verify_payload(self.hub_config, answer)
        response = self.session.post(
            self.hub_config.verify_url,
            json=payload,
            timeout=self.timeout_seconds,
        )
        return LoggedExchange(
            sequence=self._request_count,
            action=action,
            request=mask_secret_fields(payload),
            response=build_api_response(response),
        )

    # Start a fresh phonecall session.
    def start(self) -> LoggedExchange:
        return self.call({"action": "start"}, action="start")

    # Send one post-start MP3 audio turn encoded as base64.
    def send_audio(self, audio_base64: str) -> LoggedExchange:
        cleaned_audio = audio_base64.strip()
        if not cleaned_audio:
            raise ValueError("audio_base64 must not be empty.")
        return self.call({"audio": cleaned_audio}, action="audio")

