from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Suspect


def load_json_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def map_entry_to_suspect(entry: dict[str, Any]) -> Suspect:
    return Suspect(
        name=str(entry["name"]).strip(),
        surname=str(entry["surname"]).strip(),
        birth_year=int(entry["born"]),
    )


def load_suspects(path: Path) -> list[Suspect]:
    raw_data = load_json_file(path)
    payload_sent = raw_data.get("payload_sent")
    if not isinstance(payload_sent, dict):
        raise ValueError("Missing payload_sent object in verification result.")

    answer = payload_sent.get("answer")
    if not isinstance(answer, list):
        raise ValueError("Missing answer list in verification result.")

    suspects = [map_entry_to_suspect(entry) for entry in answer if isinstance(entry, dict)]
    if not suspects:
        raise ValueError("No suspects found in verification result.")

    return suspects
