# Hub submission helpers for the L4 sendit MVP2 final verification.

from typing import Any

import requests

from src.apps.L4_sendit.L4_sendit_MVP2.config import HubConfig


REQUEST_TIMEOUT_SECONDS = 30
REDACTED = "***REDACTED***"


# Build the exact payload expected by the course Hub for the sendit task.
def build_verification_payload(
    config: HubConfig,
    declaration_text: str,
) -> dict[str, Any]:
    return {
        "apikey": config.api_key,
        "task": config.task_name,
        "answer": {
            "declaration": declaration_text,
        },
    }


# Mask secret fields before writing a payload to disk or logs.
def mask_payload_for_storage(payload: dict[str, Any]) -> dict[str, Any]:
    masked_payload = dict(payload)
    masked_payload["apikey"] = REDACTED
    return masked_payload


# Send the verification payload and return a JSON-serializable response record.
def submit_verification(
    config: HubConfig,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = requests.post(
        config.verify_url,
        json=payload,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    return {
        "http_status": response.status_code,
        "body": _decode_response_body(response),
    }


# Decode a Hub response while preserving non-JSON bodies for debugging.
def _decode_response_body(response: requests.Response) -> Any:
    try:
        return response.json()
    except requests.JSONDecodeError:
        return response.text
