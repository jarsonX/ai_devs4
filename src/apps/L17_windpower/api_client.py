# Guarded HTTP client for the L17 windpower Hub API.

from __future__ import annotations

import json
from typing import Any, Protocol

import requests

from src.apps.L17_windpower.config import HubConfig
from src.apps.L17_windpower.models import ApiResponse, ConfigPoint, LoggedExchange


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


# Send windpower task requests through one guarded HTTP session.
class WindpowerApiClient:
    # Store Hub config plus request timeout and request-count guard.
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

    # Send one windpower answer action to the Hub.
    def call(self, answer: dict[str, Any]) -> LoggedExchange:
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
            request=mask_payload(payload),
            response=build_api_response(response),
        )

    # Start a new timed service window.
    def start(self) -> LoggedExchange:
        return self.call({"action": "start"})

    # Request one task report or direct documentation payload.
    def get(self, param: str) -> LoggedExchange:
        return self.call({"action": "get", "param": param})

    # Fetch one completed queued result when available.
    def get_result(self) -> LoggedExchange:
        return self.call({"action": "getResult"})

    # Queue unlock-code generation for one schedule point.
    def unlock_code_generator(self, point: ConfigPoint) -> LoggedExchange:
        return self.call(
            {
                "action": "unlockCodeGenerator",
                "startDate": point.start_date,
                "startHour": point.start_hour,
                "windMs": point.wind_ms,
                "pitchAngle": point.pitch_angle,
            }
        )

    # Submit all signed schedule points as one batch config.
    def config(self, configs: dict[str, dict[str, Any]]) -> LoggedExchange:
        return self.call({"action": "config", "configs": configs})

    # Ask the Hub to validate the final configuration.
    def done(self) -> LoggedExchange:
        return self.call({"action": "done"})
