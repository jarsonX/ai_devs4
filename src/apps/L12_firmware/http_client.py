# Shared HTTP response and request-guard helpers for the firmware APIs.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


# Describe one transport or HTTP failure in a model-safe structure.
@dataclass(frozen=True)
class ApiError:
    code: str
    message: str
    retryable: bool
    recovery_hint: str
    retry_after_seconds: int | None = None

    # Convert the error into a JSON-ready runtime record.
    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "recovery_hint": self.recovery_hint,
            "retry_after_seconds": self.retry_after_seconds,
        }


# Preserve one external API response in a stable success-or-error shape.
@dataclass(frozen=True)
class ApiResponse:
    ok: bool
    status_code: int | None
    payload: Any
    text: str
    error: ApiError | None = None

    # Convert the complete response into a JSON-ready ignored runtime record.
    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status_code": self.status_code,
            "payload": self.payload,
            "text": self.text,
            "error": self.error.to_dict() if self.error else None,
        }


# Count planned requests and block calls after the reviewed limit.
class RequestGuard:
    # Store one strict request cap and its current usage.
    def __init__(self, max_requests: int) -> None:
        if max_requests < 1:
            raise ValueError("max_requests must be at least 1.")
        self.max_requests = max_requests
        self.used_requests = 0

    # Reserve one request slot before network activity starts.
    def consume(self) -> bool:
        if self.used_requests >= self.max_requests:
            return False
        self.used_requests += 1
        return True


# Extract an integer Retry-After delay when the server provides one.
def parse_retry_after_seconds(response: requests.Response) -> int | None:
    raw_value = response.headers.get("Retry-After")
    if raw_value is None:
        return None
    try:
        return max(0, int(raw_value))
    except ValueError:
        return None


# Extract a short API message without assuming one response schema.
def extract_api_message(payload: Any, *, fallback: str) -> str:
    if isinstance(payload, dict):
        for field_name in ("message", "error", "detail"):
            value = payload.get(field_name)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return fallback


# Convert one non-success HTTP status into an actionable structured error.
def build_http_error(
    response: requests.Response,
    payload: Any,
) -> ApiError:
    status_code = response.status_code
    retry_after_seconds = parse_retry_after_seconds(response)

    if status_code == 429:
        return ApiError(
            code="rate_limited",
            message=extract_api_message(payload, fallback="The API rate limit was reached."),
            retryable=True,
            recovery_hint="Wait for the advertised delay before retrying.",
            retry_after_seconds=retry_after_seconds,
        )
    if status_code == 503:
        return ApiError(
            code="service_unavailable",
            message=extract_api_message(payload, fallback="The API service is unavailable."),
            retryable=True,
            recovery_hint="Retry the same request after a short delay.",
            retry_after_seconds=retry_after_seconds,
        )
    if status_code == 403:
        return ApiError(
            code="forbidden",
            message=extract_api_message(payload, fallback="The API rejected this request."),
            retryable=False,
            recovery_hint="Do not retry until the request or access state has been reviewed.",
            retry_after_seconds=retry_after_seconds,
        )

    return ApiError(
        code="http_error",
        message=extract_api_message(
            payload,
            fallback=f"The API returned HTTP {status_code}.",
        ),
        retryable=500 <= status_code < 600,
        recovery_hint=(
            "Retry after a short delay."
            if 500 <= status_code < 600
            else "Review the request before retrying."
        ),
        retry_after_seconds=retry_after_seconds,
    )


# Send one guarded JSON POST and normalize transport, decoding, and HTTP errors.
def post_json(
    *,
    session: requests.Session | Any,
    url: str,
    payload: dict[str, Any],
    timeout_seconds: int,
    guard: RequestGuard,
) -> ApiResponse:
    if not guard.consume():
        return ApiResponse(
            ok=False,
            status_code=None,
            payload=None,
            text="",
            error=ApiError(
                code="request_limit_reached",
                message=f"Request guard reached {guard.max_requests} calls.",
                retryable=False,
                recovery_hint="Stop the run and inspect the current state.",
            ),
        )

    try:
        response = session.post(
            url,
            json=payload,
            timeout=timeout_seconds,
        )
    except requests.Timeout:
        return ApiResponse(
            ok=False,
            status_code=None,
            payload=None,
            text="",
            error=ApiError(
                code="timeout",
                message="The API request timed out.",
                retryable=True,
                recovery_hint="Retry only if the request budget still allows it.",
            ),
        )
    except requests.RequestException as error:
        return ApiResponse(
            ok=False,
            status_code=None,
            payload=None,
            text="",
            error=ApiError(
                code="transport_error",
                message=str(error) or "The API request failed before a response arrived.",
                retryable=True,
                recovery_hint="Check connectivity and retry only within the request budget.",
            ),
        )

    try:
        decoded_payload = response.json()
    except ValueError:
        decoded_payload = None

    if not 200 <= response.status_code < 300:
        return ApiResponse(
            ok=False,
            status_code=response.status_code,
            payload=decoded_payload,
            text=response.text,
            error=build_http_error(response, decoded_payload),
        )

    if decoded_payload is None:
        return ApiResponse(
            ok=False,
            status_code=response.status_code,
            payload=None,
            text=response.text,
            error=ApiError(
                code="invalid_json",
                message="The API returned a success status with invalid JSON.",
                retryable=False,
                recovery_hint="Stop and inspect the raw response before continuing.",
            ),
        )

    return ApiResponse(
        ok=True,
        status_code=response.status_code,
        payload=decoded_payload,
        text=response.text,
    )
