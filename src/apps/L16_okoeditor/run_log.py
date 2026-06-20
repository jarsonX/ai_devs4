# JSONL event logging for L16 okoeditor runs.

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REDACTED = "***REDACTED***"


# Store the active run identifier and JSONL path together.
@dataclass(frozen=True)
class RunLog:
    run_id: str
    path: Path


# Build a filesystem-friendly run id in local sortable form.
def build_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# Create a new timestamped JSONL log file.
def create_run_log(logs_dir: Path) -> RunLog:
    logs_dir.mkdir(parents=True, exist_ok=True)
    run_id = build_run_id()
    return RunLog(run_id=run_id, path=logs_dir / f"run_{run_id}.jsonl")


# Return an ISO timestamp for one log event.
def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


# Recursively mask configured secret values in data before it reaches disk.
def mask_secrets(value: Any, secret_values: list[str] | None = None) -> Any:
    secrets = [secret for secret in (secret_values or []) if secret]

    if isinstance(value, str):
        masked = value
        for secret in secrets:
            masked = masked.replace(secret, REDACTED)
        return masked
    if isinstance(value, dict):
        masked_dict: dict[Any, Any] = {}
        for key, nested_value in value.items():
            if str(key).lower() in {"apikey", "api_key", "authorization", "access_key", "password"}:
                masked_dict[key] = REDACTED
            else:
                masked_dict[key] = mask_secrets(nested_value, secrets)
        return masked_dict
    if isinstance(value, list):
        return [mask_secrets(item, secrets) for item in value]
    if isinstance(value, tuple):
        return [mask_secrets(item, secrets) for item in value]
    return value


# Append one JSONL event to the current run log.
def append_event(
    run_log: RunLog,
    *,
    event: str,
    data: dict[str, Any],
    attempt: int | None = None,
    secret_values: list[str] | None = None,
) -> None:
    payload = {
        "timestamp": utc_timestamp(),
        "run_id": run_log.run_id,
        "attempt": attempt,
        "event": event,
        "data": mask_secrets(data, secret_values),
    }
    run_log.path.parent.mkdir(parents=True, exist_ok=True)
    with run_log.path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        file.write("\n")
