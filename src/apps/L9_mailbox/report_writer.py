# This module writes local JSON reports for bounded mailbox workbench runs.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.apps.L9_mailbox.config import AppConfig


# Persist one workbench run report under the app output directory.
def save_run_report(config: AppConfig, payload: dict[str, Any]) -> Path:
    output_path = config.paths.run_report_file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    runtime_summary = payload.get("runtime_summary", {})
    if isinstance(runtime_summary, dict):
        fetched_messages = runtime_summary.get("fetched_messages")
        if isinstance(fetched_messages, list):
            config.paths.fetched_messages_file.write_text(
                json.dumps(fetched_messages, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    return output_path
