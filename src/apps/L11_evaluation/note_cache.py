# Operator-note normalization and cache storage for the L11 evaluation workflow.

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.apps.L11_evaluation.models import NoteClassification, SensorRecord


CACHE_FORMAT_VERSION = 1


# Normalize note text conservatively so exact repeats collapse without inventing near-duplicate logic.
def normalize_operator_note(note: str) -> str:
    return " ".join(note.split()).casefold()


# Build one stable hash for a normalized note so cache keys do not depend on file names or order.
def build_note_hash(normalized_note: str) -> str:
    return hashlib.sha256(normalized_note.encode("utf-8")).hexdigest()


# Return the stable normalized-note hash for one loaded sensor record.
def get_record_note_hash(record: SensorRecord) -> str:
    normalized_note = normalize_operator_note(record.operator_notes)
    return build_note_hash(normalized_note)


# Map each file ID to the hash of its normalized operator note.
def build_record_note_hash_index(records: list[SensorRecord]) -> dict[str, str]:
    return {
        record.file_id: get_record_note_hash(record)
        for record in records
    }


# Collect unique normalized notes keyed by their stable hash.
def collect_unique_normalized_notes(records: list[SensorRecord]) -> dict[str, str]:
    unique_notes: dict[str, str] = {}

    for record in records:
        normalized_note = normalize_operator_note(record.operator_notes)
        note_hash = build_note_hash(normalized_note)
        unique_notes.setdefault(note_hash, normalized_note)

    return unique_notes


# Convert one cached note classification into a JSON-safe dictionary.
def note_classification_to_dict(classification: NoteClassification) -> dict[str, Any]:
    return {
        "note_hash": classification.note_hash,
        "normalized_note": classification.normalized_note,
        "label": classification.label,
        "confidence": classification.confidence,
    }


# Validate and convert one JSON object back into a NoteClassification.
def note_classification_from_dict(payload: dict[str, Any]) -> NoteClassification:
    note_hash = payload.get("note_hash")
    normalized_note = payload.get("normalized_note")
    label = payload.get("label")
    confidence = payload.get("confidence")

    if not isinstance(note_hash, str) or not note_hash:
        raise ValueError("Cached note classification is missing a valid note_hash.")

    if not isinstance(normalized_note, str):
        raise ValueError(f"Cached note classification {note_hash} is missing normalized_note.")

    if label not in {"claims_ok", "claims_error", "neutral_or_unclear"}:
        raise ValueError(f"Cached note classification {note_hash} has invalid label.")

    if confidence not in {"high", "medium", "low"}:
        raise ValueError(f"Cached note classification {note_hash} has invalid confidence.")

    return NoteClassification(
        note_hash=note_hash,
        normalized_note=normalized_note,
        label=label,
        confidence=confidence,
    )


# Load the local note cache, or return an empty cache when the file does not exist yet.
def load_note_cache(cache_path: Path) -> dict[str, NoteClassification]:
    if not cache_path.exists():
        return {}

    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Operator note cache must be a JSON object.")

    items = payload.get("items", [])
    if not isinstance(items, list):
        raise ValueError("Operator note cache items must be a list.")

    cache: dict[str, NoteClassification] = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Operator note cache item must be a JSON object.")

        classification = note_classification_from_dict(item)
        cache[classification.note_hash] = classification

    return cache


# Persist the note cache in stable hash order so repeated runs diff cleanly.
def save_note_cache(
    cache_path: Path,
    cache: dict[str, NoteClassification],
) -> dict[str, Any]:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": CACHE_FORMAT_VERSION,
        "items": [
            note_classification_to_dict(cache[note_hash])
            for note_hash in sorted(cache)
        ],
    }
    cache_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return payload


# Return unique normalized notes that are still missing from the local cache.
def find_uncached_notes(
    records: list[SensorRecord],
    cache: dict[str, NoteClassification],
) -> dict[str, str]:
    unique_notes = collect_unique_normalized_notes(records)
    return {
        note_hash: normalized_note
        for note_hash, normalized_note in unique_notes.items()
        if note_hash not in cache
    }
