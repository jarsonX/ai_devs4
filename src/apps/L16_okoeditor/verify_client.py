# Central verify API access for L16 okoeditor writes.

from __future__ import annotations

import json
import re
from typing import Any

import requests

from src.apps.L16_okoeditor.config import VerifyApiConfig
from src.apps.L16_okoeditor.models import UpdateInstruction, VerifyResponse


REDACTED_FLAG_MARKER = "***REDACTED_FLAG***"
FLAG_PREFIX = "".join(chr(value) for value in (70, 76, 71))
FLAG_PATTERN = re.compile(r"\{" + FLAG_PREFIX + r":[^}]+\}")


# Keep external verify calls bounded and explicit.
class OkoVerifyClient:
    # Store config plus a simple request-count guard.
    def __init__(
        self,
        config: VerifyApiConfig,
        *,
        timeout_seconds: int,
        max_requests: int,
    ) -> None:
        self._config = config
        self._timeout_seconds = timeout_seconds
        self._max_requests = max_requests
        self._request_count = 0

    # Send one prepared update instruction through the central API.
    def send_update(self, instruction: UpdateInstruction) -> tuple[dict[str, Any], VerifyResponse]:
        answer: dict[str, Any] = {
            "page": instruction.page,
            "id": instruction.record_id,
            "action": "update",
        }
        if instruction.title is not None:
            answer["title"] = instruction.title
        if instruction.content is not None:
            answer["content"] = instruction.content
        if instruction.done is not None:
            answer["done"] = instruction.done
        return self._call(answer)

    # Send the final done action only after deterministic verification passes.
    def send_done(self) -> tuple[dict[str, Any], VerifyResponse]:
        return self._call({"action": "done"})

    # Return how many verify requests were used in this run.
    def request_count(self) -> int:
        return self._request_count

    # Execute one verify request and normalize its response.
    def _call(self, answer: dict[str, Any]) -> tuple[dict[str, Any], VerifyResponse]:
        self._request_count += 1
        if self._request_count > self._max_requests:
            raise ValueError("The verify request guard was exceeded.")

        payload = {
            "apikey": self._config.api_key,
            "task": self._config.task_name,
            "answer": answer,
        }
        response = requests.post(
            self._config.verify_url,
            json=payload,
            timeout=self._timeout_seconds,
        )
        normalized = VerifyResponse(
            status_code=response.status_code,
            payload=parse_json_payload(response.text),
            text=response.text,
        )
        return masked_request(payload), normalized


# Parse JSON when possible and keep non-JSON responses as None payload.
def parse_json_payload(text: str) -> Any | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# Build a secret-safe request payload for logs.
def masked_request(payload: dict[str, Any]) -> dict[str, Any]:
    safe = dict(payload)
    safe["apikey"] = "***REDACTED***"
    return safe


# Return whether one response contains a FLAG anywhere in its visible content.
def response_contains_flag(response: VerifyResponse) -> bool:
    haystack = response.text
    if response.payload is not None:
        haystack = f"{haystack}\n{json.dumps(response.payload, ensure_ascii=False)}"
    return REDACTED_FLAG_MARKER in haystack or FLAG_PATTERN.search(haystack) is not None


# Build a compact response summary that is safe for JSONL logs.
def response_summary_for_log(response: VerifyResponse) -> dict[str, Any]:
    return {
        "status_code": response.status_code,
        "has_json_payload": response.payload is not None,
        "payload": response.payload,
        "flag_found": response_contains_flag(response),
    }
