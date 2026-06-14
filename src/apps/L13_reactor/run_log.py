# Runtime JSONL logging for reactor command and response history.

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.apps.L13_reactor.hub_client import HubResponse


# Create a timestamped log path for one isolated controller run.
def create_run_log_path(logs_dir: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%fZ")
    return logs_dir / f"reactor_run_{timestamp}.jsonl"


# Convert a Hub response to the full JSON-safe runtime representation.
def hub_response_to_dict(response: HubResponse) -> dict[str, Any]:
    return {
        "status_code": response.status_code,
        "payload": response.payload,
        "text": response.text,
    }


# Append one command exchange without placing the API key in the log.
def append_command_event(
    log_path: Path,
    *,
    sequence: int,
    command: str,
    masked_request: dict[str, Any],
    response: HubResponse,
) -> None:
    event = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "sequence": sequence,
        "command": command,
        "request": masked_request,
        "response": hub_response_to_dict(response),
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=True) + "\n")
