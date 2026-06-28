# Guarded HTTP client for the L19 filesystem Hub API.

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

import requests

from src.apps.L19_filesystem.config import HubConfig


REDACTED = "***REDACTED***"
FLAG_PREFIX = "".join(chr(value) for value in (70, 76, 71))
FLAG_PATTERN = re.compile(r"\{" + FLAG_PREFIX + r":[^}]+\}")


# Define the small subset of requests.Session used by the client.
class SessionProtocol(Protocol):
    # Send one POST request through an injected HTTP session.
    def post(self, *args: Any, **kwargs: Any) -> requests.Response:
        ...


# Store one decoded or raw Hub response.
@dataclass(frozen=True)
class ApiResponse:
    status_code: int
    payload: Any | None
    text: str


# Store one masked request and its full response for runtime data.
@dataclass(frozen=True)
class LoggedExchange:
    sequence: int
    action: str
    request: dict[str, Any]
    response: ApiResponse

    # Convert the exchange into JSON-safe output.
    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "action": self.action,
            "request": self.request,
            "response": {
                "status_code": self.response.status_code,
                "payload": self.response.payload,
                "text": self.response.text,
                "flag_found": response_contains_flag(self.response),
            },
        }


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


# Return whether one response contains a FLAG anywhere in its visible content.
def response_contains_flag(response: ApiResponse) -> bool:
    haystack = response.text
    if response.payload is not None:
        haystack = f"{haystack}\n{json.dumps(response.payload, ensure_ascii=False)}"
    return FLAG_PATTERN.search(haystack) is not None


# Send filesystem task actions through one guarded HTTP session.
class FilesystemVerifyClient:
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

    # Send one answer object or batch answer to the Hub.
    def call(self, answer: dict[str, Any] | list[dict[str, Any]], *, action: str) -> LoggedExchange:
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

    # Ask the Hub for the task-specific filesystem contract.
    def help(self) -> LoggedExchange:
        return self.call({"action": "help"}, action="help")

    # Clear the remote virtual filesystem.
    def reset(self) -> LoggedExchange:
        return self.call({"action": "reset"}, action="reset")

    # Create directories and files as one batch operation.
    def apply_batch(self, operations: list[dict[str, Any]]) -> LoggedExchange:
        return self.call(operations, action="batch")

    # Ask the Hub to validate the final virtual filesystem.
    def done(self) -> LoggedExchange:
        return self.call({"action": "done"}, action="done")
