# Guarded HTTP client for the L21 radiomonitoring Hub API.

from __future__ import annotations

from typing import Any, Protocol

import requests

from src.apps.L21_radiomonitoring.config import HubConfig
from src.apps.L21_radiomonitoring.models import ApiResponse, LoggedExchange


REDACTED = "***REDACTED***"


# Define the small subset of requests.Session used by the client.
class SessionProtocol(Protocol):
    # Send one POST request through an injected HTTP session.
    def post(self, *args: Any, **kwargs: Any) -> requests.Response:
        ...


# Read a JSON response when possible while keeping text fallback.
def build_api_response(response: requests.Response) -> ApiResponse:
    try:
        payload = response.json()
    except requests.JSONDecodeError:
        payload = None
    return ApiResponse(
        status_code=response.status_code,
        payload=payload,
        text=response.text,
    )


# Remove the API key before preserving a request in runtime data.
def mask_payload(payload: dict[str, Any]) -> dict[str, Any]:
    masked_payload = dict(payload)
    if "apikey" in masked_payload:
        masked_payload["apikey"] = REDACTED
    return masked_payload


# Send radiomonitoring task actions through one guarded HTTP session.
class RadiomonitoringVerifyClient:
    # Store Hub config plus timeout and request-count guard.
    def __init__(
        self,
        config: HubConfig,
        *,
        timeout_seconds: int,
        max_requests: int,
        session: SessionProtocol | None = None,
    ) -> None:
        self.hub_config = config
        self.timeout_seconds = timeout_seconds
        self.max_requests = max_requests
        self.session = session or requests.Session()
        self._request_count = 0

    # Return how many Hub requests have been used in this run.
    def request_count(self) -> int:
        return self._request_count

    # Send one answer object to the Hub.
    def call(self, answer: dict[str, Any], *, action: str) -> LoggedExchange:
        self._request_count += 1
        if self._request_count > self.max_requests:
            raise ValueError("The Hub request guard was exceeded.")

        payload = {
            "apikey": self.hub_config.api_key,
            "task": self.hub_config.task_name,
            "answer": answer,
        }
        response = self.session.post(
            self.hub_config.verify_url,
            json=payload,
            timeout=self.timeout_seconds,
        )
        return LoggedExchange(
            sequence=self._request_count,
            action=action,
            request=mask_payload(payload),
            response=build_api_response(response),
        )

    # Start a fresh listening session.
    def start(self) -> LoggedExchange:
        return self.call({"action": "start"}, action="start")

    # Fetch one captured radio signal.
    def listen(self) -> LoggedExchange:
        return self.call({"action": "listen"}, action="listen")

    # Submit the final report to the Hub.
    def transmit(self, answer: dict[str, Any]) -> LoggedExchange:
        return self.call(answer, action="transmit")
