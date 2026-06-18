# Runtime JSONL logging for discovery traces and workflow milestones.

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


# Append one JSON-safe event to the active trace log file.
def append_trace_event(
    log_path: Path,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    event = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "event_type": event_type,
        "payload": payload,
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=True) + "\n")

