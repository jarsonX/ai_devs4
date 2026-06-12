# Deterministic validation for L11 sensor measurement records.

from __future__ import annotations

from src.apps.L11_evaluation.models import (
    MeasurementField,
    MeasurementFinding,
    SensorIssue,
    SensorName,
    SensorRecord,
)
from src.apps.L11_evaluation.sensor_rules import (
    MEASUREMENT_FIELDS,
    get_active_measurement_fields,
    get_inactive_measurement_fields,
    get_sensor_rule,
    is_value_in_active_range,
    parse_sensor_type,
)


REQUIRED_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "sensor_type",
    "timestamp",
    *MEASUREMENT_FIELDS,
    "operator_notes",
)


# Build one issue for a missing top-level field in the sensor JSON payload.
def build_missing_required_field_issue(
    file_id: str,
    field_name: str,
) -> SensorIssue:
    measurement_field = (
        field_name
        if field_name in MEASUREMENT_FIELDS
        else None
    )

    return SensorIssue(
        file_id=file_id,
        kind="missing_required_field",
        message=f"Missing required field: {field_name}",
        field=measurement_field,
    )


# Build one issue for a sensor_type value that cannot be parsed into known sensors.
def build_unknown_sensor_type_issue(
    record: SensorRecord,
    error: ValueError,
) -> SensorIssue:
    return SensorIssue(
        file_id=record.file_id,
        kind="unknown_sensor_type",
        message=f"Unknown sensor_type value '{record.sensor_type}': {error}",
        value=record.sensor_type,
    )


# Build one issue for an active measurement field that falls outside its valid range.
def build_active_value_out_of_range_issue(
    record: SensorRecord,
    sensor_name: SensorName,
) -> SensorIssue:
    rule = get_sensor_rule(sensor_name)
    value = record.measurements[rule.measurement_field]

    return SensorIssue(
        file_id=record.file_id,
        kind="active_value_out_of_range",
        message=(
            f"{rule.measurement_field}={value} is outside the valid range "
            f"{rule.min_value}..{rule.max_value} for sensor '{sensor_name}'."
        ),
        field=rule.measurement_field,
        value=value,
    )


# Build one issue for a field that should stay exactly zero for inactive sensors.
def build_inactive_field_non_zero_issue(
    record: SensorRecord,
    field: MeasurementField,
) -> SensorIssue:
    value = record.measurements[field]

    return SensorIssue(
        file_id=record.file_id,
        kind="inactive_field_non_zero",
        message=f"{field} must be 0 for inactive sensors, but is {value}.",
        field=field,
        value=value,
    )


# Return required fields missing from the raw JSON payload.
def find_missing_required_fields(record: SensorRecord) -> list[str]:
    return [
        field_name
        for field_name in REQUIRED_TOP_LEVEL_FIELDS
        if field_name not in record.raw_payload
    ]


# Parse active sensor names only when sensor_type exists in the raw payload.
def resolve_active_sensors(record: SensorRecord) -> tuple[tuple[SensorName, ...], list[SensorIssue]]:
    if "sensor_type" not in record.raw_payload:
        return (), []

    try:
        active_sensors = parse_sensor_type(record.sensor_type)
    except ValueError as error:
        return (), [build_unknown_sensor_type_issue(record, error)]

    return active_sensors, []


# Check only active measurement fields that actually exist in the source payload.
def validate_active_measurements(
    record: SensorRecord,
    active_sensors: tuple[SensorName, ...],
) -> list[SensorIssue]:
    issues: list[SensorIssue] = []

    for sensor_name in active_sensors:
        rule = get_sensor_rule(sensor_name)
        if rule.measurement_field not in record.raw_payload:
            continue

        value = record.measurements[rule.measurement_field]
        if not is_value_in_active_range(sensor_name, value):
            issues.append(build_active_value_out_of_range_issue(record, sensor_name))

    return issues


# Check only inactive measurement fields that actually exist in the source payload.
def validate_inactive_measurements(
    record: SensorRecord,
    active_sensors: tuple[SensorName, ...],
) -> list[SensorIssue]:
    issues: list[SensorIssue] = []

    for field in get_inactive_measurement_fields(active_sensors):
        if field not in record.raw_payload:
            continue

        value = record.measurements[field]
        if float(value) != 0.0:
            issues.append(build_inactive_field_non_zero_issue(record, field))

    return issues


# Validate one sensor record against required fields, sensor naming, and measurement rules.
def validate_sensor_record(record: SensorRecord) -> MeasurementFinding:
    issues = [
        build_missing_required_field_issue(record.file_id, field_name)
        for field_name in find_missing_required_fields(record)
    ]

    active_sensors, sensor_type_issues = resolve_active_sensors(record)
    issues.extend(sensor_type_issues)

    if not sensor_type_issues:
        issues.extend(validate_active_measurements(record, active_sensors))
        issues.extend(validate_inactive_measurements(record, active_sensors))

    return MeasurementFinding(
        file_id=record.file_id,
        sensor_type=record.sensor_type,
        measurements_ok=not issues,
        active_sensors=active_sensors,
        active_fields=get_active_measurement_fields(active_sensors),
        issues=issues,
    )


# Validate a batch of records in order so reports stay aligned with source file order.
def validate_sensor_records(records: list[SensorRecord]) -> list[MeasurementFinding]:
    return [validate_sensor_record(record) for record in records]
