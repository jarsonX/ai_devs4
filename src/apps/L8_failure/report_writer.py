# Report and artifact writing helpers for the L8 workflow.

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, cast


# Convert dataclasses and paths into JSON-friendly report values.
def to_jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return to_jsonable(asdict(cast(Any, value)))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_jsonable(nested_value) for key, nested_value in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    return value


# Write pretty JSON so learners can inspect runtime artifacts by hand.
def write_json_file(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(to_jsonable(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# Write JSONL artifacts where one line corresponds to one source event.
def write_jsonl_file(path: Path, rows: list[Any]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(to_jsonable(row), ensure_ascii=False))
            file.write("\n")
