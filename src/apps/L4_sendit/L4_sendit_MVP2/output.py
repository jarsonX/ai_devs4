# Output helpers for files produced by the L4 sendit MVP2 Stage 1-6 workflow.

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel


# Save a readable JSON artifact for transparent pipeline inspection.
def save_json(output_file: Path, data: Any) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(_to_json_ready(data), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# Save the human-readable explanation of the current run.
def save_run_report(output_file: Path, report_text: str) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(report_text, encoding="utf-8")


# Save a UTF-8 text artifact produced by deterministic rendering.
def save_text(output_file: Path, text: str) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(text, encoding="utf-8")


# Convert dataclasses, Pydantic models, and nested values into JSON-ready data.
def _to_json_ready(data: Any) -> Any:
    if isinstance(data, BaseModel):
        return _to_json_ready(data.model_dump(mode="json"))
    if is_dataclass(data):
        return _to_json_ready(asdict(data))
    if isinstance(data, list):
        return [_to_json_ready(item) for item in data]
    if isinstance(data, tuple):
        return [_to_json_ready(item) for item in data]
    if isinstance(data, dict):
        return {key: _to_json_ready(value) for key, value in data.items()}

    return data
