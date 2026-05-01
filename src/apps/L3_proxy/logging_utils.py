# This module writes masked technical event logs for the L3_proxy app.

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .config import AppConfig


REDACTED = "***REDACTED***"
EVENTS_LOG_FILENAME = "events.jsonl"
SENSITIVE_KEYS = {
    "apikey",
    "api_key",
    "authorization",
    "code",
    "known_security_code",
    "openai_api_key",
    "ai_devs_api_key",
    "proxy_api_url",
    "hub_verify_url",
    "url",
    "endpoint",
}


# This helper checks whether one dictionary key should be hidden in logs.
def is_sensitive_key(key: str) -> bool:
    normalized_key = key.lower()
    return normalized_key in SENSITIVE_KEYS or "token" in normalized_key


# This helper masks sensitive values in nested JSON-like payloads.
def mask_sensitive_payload(value: Any) -> Any:
    if isinstance(value, dict):
        masked: dict[str, Any] = {}
        for key, nested_value in value.items():
            if is_sensitive_key(str(key)):
                masked[key] = REDACTED
                continue

            masked[key] = mask_sensitive_payload(nested_value)

        return masked

    if isinstance(value, list):
        return [mask_sensitive_payload(item) for item in value]

    return value


# This helper builds the timestamped event envelope stored in the JSONL log.
def build_log_event(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "payload": mask_sensitive_payload(payload),
    }


# This helper appends one masked technical event to the application JSONL log.
def append_log_event(
    config: AppConfig,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    config.logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = config.logs_dir / EVENTS_LOG_FILENAME
    event = build_log_event(event_type, payload)

    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(event, ensure_ascii=False))
        log_file.write("\n")
