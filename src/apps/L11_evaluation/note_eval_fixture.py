# Curated note-eval fixture loading and scoring for the L11 evaluation workflow.

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.apps.L11_evaluation.models import NoteLabel


FIXTURE_FORMAT_VERSION = 1


# Store one curated note example used to sanity-check the classifier before a full run.
@dataclass(frozen=True)
class NoteEvalExample:
    case_id: str
    note_text: str
    expected_label: NoteLabel
    rationale: str


# Store one local eval summary so prompt changes can be compared deterministically.
@dataclass(frozen=True)
class NoteEvalResult:
    total_cases: int
    correct_cases: int
    accuracy: float
    mismatches: list[dict[str, str]]


# Convert one JSON object into a validated curated note example.
def note_eval_example_from_dict(payload: dict[str, Any]) -> NoteEvalExample:
    case_id = payload.get("case_id")
    note_text = payload.get("note_text")
    expected_label = payload.get("expected_label")
    rationale = payload.get("rationale")

    if not isinstance(case_id, str) or not case_id:
        raise ValueError("Fixture item is missing a valid case_id.")

    if not isinstance(note_text, str) or not note_text.strip():
        raise ValueError(f"Fixture item {case_id} is missing note_text.")

    if expected_label not in {"claims_ok", "claims_error", "neutral_or_unclear"}:
        raise ValueError(f"Fixture item {case_id} has invalid expected_label.")

    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError(f"Fixture item {case_id} is missing rationale.")

    return NoteEvalExample(
        case_id=case_id,
        note_text=note_text,
        expected_label=expected_label,
        rationale=rationale,
    )


# Load the curated note-eval fixture from a local JSON file.
def load_note_eval_fixture(fixture_path: Path) -> list[NoteEvalExample]:
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Note eval fixture must be a JSON object.")

    version = payload.get("version")
    if version != FIXTURE_FORMAT_VERSION:
        raise ValueError(
            f"Note eval fixture version must be {FIXTURE_FORMAT_VERSION}, got {version!r}."
        )

    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError("Note eval fixture items must be a list.")

    examples = [note_eval_example_from_dict(item) for item in items if isinstance(item, dict)]
    if len(examples) != len(items):
        raise ValueError("Each fixture item must be a JSON object.")

    if not examples:
        raise ValueError("Note eval fixture must contain at least one example.")

    case_ids = [example.case_id for example in examples]
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("Note eval fixture case_id values must be unique.")

    return examples


# Return fixture examples keyed by case_id for stable local eval comparisons.
def build_note_eval_index(examples: list[NoteEvalExample]) -> dict[str, NoteEvalExample]:
    return {
        example.case_id: example
        for example in examples
    }


# Score predicted labels against the curated fixture before a full model classification run.
def evaluate_note_predictions(
    examples: list[NoteEvalExample],
    predictions: dict[str, NoteLabel],
) -> NoteEvalResult:
    mismatches: list[dict[str, str]] = []
    correct_cases = 0

    for example in examples:
        predicted_label = predictions.get(example.case_id)
        if predicted_label == example.expected_label:
            correct_cases += 1
            continue

        mismatches.append(
            {
                "case_id": example.case_id,
                "expected_label": example.expected_label,
                "predicted_label": predicted_label or "missing",
            }
        )

    total_cases = len(examples)
    return NoteEvalResult(
        total_cases=total_cases,
        correct_cases=correct_cases,
        accuracy=correct_cases / total_cases,
        mismatches=mismatches,
    )
