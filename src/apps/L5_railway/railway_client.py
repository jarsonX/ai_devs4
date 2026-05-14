# Send railway API requests with retry and rate-limit protections.

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import time
from typing import Any, Callable

import requests

from src.apps.L5_railway.config import HubConfig


DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_REQUEST_ATTEMPTS = 5
INITIAL_503_BACKOFF_SECONDS = 2
MAX_503_BACKOFF_SECONDS = 30
FALLBACK_429_WAIT_SECONDS = 30


# Store one decoded railway API response together with transport metadata.
@dataclass(frozen=True)
class RailwayApiResponse:
    http_status: int
    body: Any
    headers: dict[str, str]
    attempts_used: int


# Talk to the railway API while enforcing retry and rate-limit waits.
class RailwayApiClient:
    # Configure one reusable client instance for the railway verification API.
    def __init__(
        self,
        config: HubConfig,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        max_request_attempts: int = DEFAULT_MAX_REQUEST_ATTEMPTS,
        session: requests.Session | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        time_fn: Callable[[], float] = time.time,
    ) -> None:
        self.config = config
        self.timeout = timeout
        self.max_request_attempts = max_request_attempts
        self.session = session or requests.Session()
        self._sleep = sleep_fn
        self._time = time_fn
        self._next_request_not_before = 0.0

    # Send one railway action request and return the decoded API response.
    def request_action(self, action: str, **action_fields: Any) -> RailwayApiResponse:
        if self.max_request_attempts < 1:
            raise ValueError("max_request_attempts must be at least 1.")

        payload = build_action_payload(self.config, action, action_fields)

        for attempt in range(1, self.max_request_attempts + 1):
            self._wait_for_request_window()
            response = self.session.post(
                self.config.verify_url,
                json=payload,
                timeout=self.timeout,
            )
            self._update_request_window(response)

            if response.status_code in (429, 503) and attempt < self.max_request_attempts:
                self._apply_retry_wait(response, attempt)
                continue

            return build_api_response(response, attempt)

        raise RuntimeError("Railway API request loop exited without a response.")

    # Wait until the stored rate-limit window allows the next request.
    def _wait_for_request_window(self) -> None:
        wait_seconds = self._next_request_not_before - self._time()
        if wait_seconds > 0:
            self._sleep(wait_seconds)

    # Update the next allowed request time from rate-limit headers.
    def _update_request_window(self, response: requests.Response) -> None:
        wait_seconds = get_rate_limit_wait_seconds(response, self._time())
        if wait_seconds is None:
            return

        self._extend_request_window(wait_seconds)

    # Add retry waiting for a retryable response without shortening existing waits.
    def _apply_retry_wait(self, response: requests.Response, attempt: int) -> None:
        if response.status_code == 429 and get_rate_limit_wait_seconds(response, self._time()) is None:
            self._extend_request_window(FALLBACK_429_WAIT_SECONDS)
            return

        if response.status_code == 503:
            self._extend_request_window(calculate_503_backoff_seconds(attempt))

    # Extend the next request window without shortening an existing wait.
    def _extend_request_window(self, wait_seconds: float) -> None:
        bounded_wait_seconds = max(0.0, wait_seconds)
        self._next_request_not_before = max(
            self._next_request_not_before,
            self._time() + bounded_wait_seconds,
        )


# Build one raw Hub payload for a railway API action.
def build_action_payload(
    config: HubConfig,
    action: str,
    action_fields: dict[str, Any],
) -> dict[str, Any]:
    normalized_action = action.strip()
    if not normalized_action:
        raise ValueError("action must be a non-empty string.")

    return {
        "apikey": config.api_key,
        "task": config.task_name,
        "answer": {
            "action": normalized_action,
            **action_fields,
        },
    }


# Convert one requests response into a stable serializable object.
def build_api_response(response: requests.Response, attempts_used: int) -> RailwayApiResponse:
    return RailwayApiResponse(
        http_status=response.status_code,
        body=decode_response_body(response),
        headers=dict(response.headers.items()),
        attempts_used=attempts_used,
    )


# Decode a railway API response while preserving plain text fallback.
def decode_response_body(response: requests.Response) -> Any:
    try:
        return response.json()
    except requests.JSONDecodeError:
        return response.text


# Read how long the client should wait because of rate-limit headers.
def get_rate_limit_wait_seconds(response: requests.Response, now_timestamp: float) -> float | None:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        parsed_retry_after = parse_retry_after_value(retry_after, now_timestamp)
        if parsed_retry_after is not None:
            return parsed_retry_after

    remaining_requests = extract_remaining_requests(response.headers)
    reset_wait_seconds = extract_reset_wait_seconds(response.headers, now_timestamp)
    if remaining_requests is not None and remaining_requests <= 0 and reset_wait_seconds is not None:
        return reset_wait_seconds

    return None


# Read a remaining-requests header using common header-name fragments.
def extract_remaining_requests(headers: Mapping[str, str]) -> int | None:
    for header_name, header_value in headers.items():
        lowered_name = header_name.lower()
        if "remaining" not in lowered_name:
            continue
        if "rate" not in lowered_name and "limit" not in lowered_name:
            continue

        try:
            return int(float(header_value.strip()))
        except (AttributeError, ValueError):
            return None

    return None


# Read a reset-like header and convert it to a wait duration.
def extract_reset_wait_seconds(
    headers: Mapping[str, str],
    now_timestamp: float,
) -> float | None:
    for header_name, header_value in headers.items():
        lowered_name = header_name.lower()
        if "reset" not in lowered_name:
            continue
        if "rate" not in lowered_name and "limit" not in lowered_name:
            continue

        return parse_reset_header_value(header_value, now_timestamp)

    return None


# Parse Retry-After as seconds or an HTTP date.
def parse_retry_after_value(value: str, now_timestamp: float) -> float | None:
    stripped_value = value.strip()
    if not stripped_value:
        return None

    try:
        numeric_value = float(stripped_value)
    except ValueError:
        parsed_datetime = parse_http_datetime(stripped_value)
        if parsed_datetime is None:
            return None

        return max(0.0, parsed_datetime.timestamp() - now_timestamp)

    return max(0.0, numeric_value)


# Parse a reset-like header as seconds, unix timestamp, milliseconds, or HTTP date.
def parse_reset_header_value(value: str, now_timestamp: float) -> float | None:
    stripped_value = value.strip()
    if not stripped_value:
        return None

    try:
        numeric_value = float(stripped_value)
    except ValueError:
        parsed_datetime = parse_http_datetime(stripped_value)
        if parsed_datetime is None:
            return None

        return max(0.0, parsed_datetime.timestamp() - now_timestamp)

    if numeric_value >= 1_000_000_000_000:
        return max(0.0, (numeric_value / 1000.0) - now_timestamp)

    if numeric_value >= 1_000_000_000:
        return max(0.0, numeric_value - now_timestamp)

    return max(0.0, numeric_value)


# Parse one HTTP date header into a timezone-aware datetime.
def parse_http_datetime(value: str) -> datetime | None:
    try:
        parsed_datetime = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None

    if parsed_datetime.tzinfo is None:
        return parsed_datetime.replace(tzinfo=timezone.utc)

    return parsed_datetime


# Calculate a bounded linear backoff delay for retried HTTP 503 responses.
def calculate_503_backoff_seconds(attempt: int) -> float:
    return min(float(INITIAL_503_BACKOFF_SECONDS * attempt), float(MAX_503_BACKOFF_SECONDS))
