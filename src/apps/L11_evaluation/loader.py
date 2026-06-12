# JSON loading and file discovery for the L11 evaluation app.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from src.apps.L11_evaluation.models import MeasurementField, SensorIssue, SensorRecord
from src.apps.L11_evaluation.sensor_rules import MEASUREMENT_FIELDS


# Return reproducibly ordered JSON files from the sensor input directory.
def discover_sensor_files(sensors_dir: Path) -> list[Path]:
    if not sensors_dir.exists():
        raise FileNotFoundError(f"Sensor input directory does not exist: {sensors_dir}")

    if not sensors_dir.is_dir():
        raise NotADirectoryError(f"Sensor input path is not a directory: {sensors_dir}")

    return sorted(
        path
        for path in sensors_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".json"
    )


# Derive the task-facing file ID from the sensor file name.
def extract_file_id(source_path: Path) -> str:
    file_id = source_path.stem.strip()
    if not file_id:
        raise ValueError(f"Could not derive file_id from path: {source_path}")

    return file_id


# Keep numeric normalization lightweight while preserving the raw payload for later checks.
def normalize_numeric_value(value: object) -> int | float:
    if isinstance(value, bool):
        return 0

    if isinstance(value, (int, float)):
        return value

    return 0


# Normalize timestamp values without guessing when the JSON type is wrong.
def normalize_timestamp(value: object) -> int:
    if isinstance(value, bool):
        return 0

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    return 0


# Build one SensorRecord while keeping the original payload for later validation.
def build_sensor_record(source_path: Path, payload: dict[str, Any]) -> SensorRecord:
    measurements: dict[MeasurementField, int | float] = {
        field: normalize_numeric_value(payload.get(field))
        for field in MEASUREMENT_FIELDS
    }

    sensor_type = payload.get("sensor_type")
    operator_notes = payload.get("operator_notes")

    return SensorRecord(
        file_id=extract_file_id(source_path),
        source_path=str(source_path),
        sensor_type=sensor_type if isinstance(sensor_type, str) else "",
        timestamp=normalize_timestamp(payload.get("timestamp")),
        measurements=measurements,
        operator_notes=operator_notes if isinstance(operator_notes, str) else "",
        raw_payload=payload,
    )


# Read one sensor file and require the top-level payload to be a JSON object.
def load_sensor_record(source_path: Path) -> SensorRecord:
    with source_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError("Sensor record must be a JSON object.")

    typed_payload = cast(dict[str, Any], payload)
    return build_sensor_record(source_path, typed_payload)


# Convert a loader failure into a deterministic issue tied to one file ID.
def build_malformed_record_issue(source_path: Path, error: Exception) -> SensorIssue:
    return SensorIssue(
        file_id=extract_file_id(source_path),
        kind="malformed_record",
        message=f"Failed to load sensor record: {error}",
    )


# Load every sensor JSON file and separate valid records from malformed inputs.
def load_sensor_records(sensors_dir: Path) -> tuple[list[SensorRecord], list[SensorIssue]]:
    records: list[SensorRecord] = []
    issues: list[SensorIssue] = []

    for source_path in discover_sensor_files(sensors_dir):
        try:
            records.append(load_sensor_record(source_path))
        except (OSError, json.JSONDecodeError, ValueError) as error:
            issues.append(build_malformed_record_issue(source_path, error))

    return records, issues
