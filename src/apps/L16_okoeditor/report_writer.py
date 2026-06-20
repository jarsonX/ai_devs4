# Runtime artifact writing for the L16 okoeditor workflow.

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.apps.L16_okoeditor.config import AppPaths


UUID_PATTERN = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)


# Write one JSON artifact under the app runtime directory.
def write_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


# Write one text artifact under the app runtime directory.
def write_text(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)


# Remove exposed access-key-like values from HTML snapshots and runtime text files.
def sanitize_runtime_text(content: str) -> str:
    return UUID_PATTERN.sub("***REDACTED***", content)


# Write one HTML snapshot for offline parser inspection.
def write_html_snapshot(paths: AppPaths, run_id: str, label: str, html: str) -> str:
    return write_text(paths.cache_dir / f"{run_id}_{label}.html", sanitize_runtime_text(html))


# Write the deterministic dry-run or apply plan report.
def write_plan_report(paths: AppPaths, run_id: str, report: dict[str, Any]) -> str:
    return write_json(paths.output_dir / f"{run_id}_plan.json", report)


# Write the final raw done response so FLAG inspection is possible later.
def write_final_response(paths: AppPaths, run_id: str, content: str) -> str:
    return write_text(paths.output_dir / f"{run_id}_done_response.txt", sanitize_runtime_text(content))
