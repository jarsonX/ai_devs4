# Runtime report writing for the L15_savethem workflow.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.apps.L15_savethem.config import AppPaths


# Persist one JSON artifact under the app output directory.
def write_json_file(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    return path


# Save the main run report and return the written path.
def save_run_report(paths: AppPaths, payload: dict[str, Any]) -> Path:
    return write_json_file(paths.run_report_file, payload)


# Save normalized mission knowledge for local inspection.
def save_knowledge_report(paths: AppPaths, payload: dict[str, Any]) -> Path:
    return write_json_file(paths.knowledge_file, payload)


# Save the chosen route plan for local inspection.
def save_route_report(paths: AppPaths, payload: dict[str, Any]) -> Path:
    return write_json_file(paths.route_file, payload)

