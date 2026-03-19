from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


REDACTED = "***REDACTED***"
SENSITIVE_KEYS = {
    "apikey",
    "api_key",
    "openai_api_key",
    "authorization",
    "power_plants_url",
    "location_api_url",
    "access_level_api_url",
    "verify_api_url",
    "url",
    "endpoint",
}


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def sanitize_for_storage(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}

        for key, nested_value in value.items():
            if key.lower() in SENSITIVE_KEYS:
                sanitized[key] = REDACTED
                continue

            sanitized[key] = sanitize_for_storage(nested_value)

        return sanitized

    if isinstance(value, list):
        return [sanitize_for_storage(item) for item in value]

    return value


def save_run_artifact(output_json_path: Path, data: dict[str, Any]) -> Path:
    ensure_directory(output_json_path.parent)

    artifact = {
        "timestamp": datetime.now().isoformat(),
        "data": sanitize_for_storage(data),
    }

    with output_json_path.open("w", encoding="utf-8") as file:
        json.dump(artifact, file, indent=2, ensure_ascii=False)

    return output_json_path
