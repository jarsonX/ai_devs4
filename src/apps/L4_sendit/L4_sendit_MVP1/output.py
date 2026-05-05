# Output helpers for files produced by the L4 sendit MVP1 learning app.

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


# Save the final declaration text as the Stage 1 output artifact.
def save_declaration(output_file: Path, declaration_text: str) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(declaration_text, encoding="utf-8")


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


# Convert dataclasses and nested values into JSON-serializable structures.
def _to_json_ready(data: Any) -> Any:
    if is_dataclass(data):
        return asdict(data)

    return data
