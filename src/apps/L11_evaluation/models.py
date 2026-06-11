# Data structures shared by the L11 evaluation workflow.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


SensorName = Literal["temperature", "pressure", "water", "voltage", "humidity"]
MeasurementField = Literal[
    "temperature_K",
    "pressure_bar",
    "water_level_meters",
    "voltage_supply_v",
    "humidity_percent",
]
NoteLabel = Literal["claims_ok", "claims_error", "neutral_or_unclear"]
ConfidenceLabel = Literal["high", "medium", "low"]
IssueKind = Literal[
    "active_value_out_of_range",
    "inactive_field_non_zero",
    "unknown_sensor_type",
    "missing_required_field",
    "malformed_record",
    "operator_claims_ok_but_data_invalid",
    "operator_claims_error_but_data_ok",
]


# Store the valid field and range contract for one sensor type.
@dataclass(frozen=True)
class SensorRule:
    sensor_name: SensorName
    measurement_field: MeasurementField
    min_value: float
    max_value: float


# Store one parsed sensor JSON file with source identity preserved.
@dataclass(frozen=True)
class SensorRecord:
    file_id: str
    source_path: str
    sensor_type: str
    timestamp: int
    measurements: dict[MeasurementField, int | float]
    operator_notes: str
    raw_payload: dict[str, Any] = field(default_factory=dict)


# Store one deterministic or semantic problem found in a sensor file.
@dataclass(frozen=True)
class SensorIssue:
    file_id: str
    kind: IssueKind
    message: str
    field: MeasurementField | None = None
    value: int | float | str | None = None


# Store the deterministic measurement status before note semantics are applied.
@dataclass(frozen=True)
class MeasurementFinding:
    file_id: str
    sensor_type: str
    measurements_ok: bool
    active_sensors: tuple[SensorName, ...]
    active_fields: tuple[MeasurementField, ...]
    issues: list[SensorIssue] = field(default_factory=list)


# Store the cached semantic label for one normalized operator note.
@dataclass(frozen=True)
class NoteClassification:
    note_hash: str
    normalized_note: str
    label: NoteLabel
    confidence: ConfidenceLabel


# Store the final local result before the Hub request adds an API key.
@dataclass(frozen=True)
class EvaluationAnswer:
    recheck: list[str]
