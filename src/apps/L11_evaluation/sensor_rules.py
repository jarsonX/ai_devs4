# Sensor rule definitions for the L11 evaluation app.

from __future__ import annotations

from src.apps.L11_evaluation.models import MeasurementField, SensorName, SensorRule


MEASUREMENT_FIELDS: tuple[MeasurementField, ...] = (
    "temperature_K",
    "pressure_bar",
    "water_level_meters",
    "voltage_supply_v",
    "humidity_percent",
)

SENSOR_RULES: tuple[SensorRule, ...] = (
    SensorRule(
        sensor_name="temperature",
        measurement_field="temperature_K",
        min_value=553.0,
        max_value=873.0,
    ),
    SensorRule(
        sensor_name="pressure",
        measurement_field="pressure_bar",
        min_value=60.0,
        max_value=160.0,
    ),
    SensorRule(
        sensor_name="water",
        measurement_field="water_level_meters",
        min_value=5.0,
        max_value=15.0,
    ),
    SensorRule(
        sensor_name="voltage",
        measurement_field="voltage_supply_v",
        min_value=229.0,
        max_value=231.0,
    ),
    SensorRule(
        sensor_name="humidity",
        measurement_field="humidity_percent",
        min_value=40.0,
        max_value=80.0,
    ),
)

SENSOR_RULES_BY_NAME: dict[SensorName, SensorRule] = {
    rule.sensor_name: rule for rule in SENSOR_RULES
}
SENSOR_RULES_BY_FIELD: dict[MeasurementField, SensorRule] = {
    rule.measurement_field: rule for rule in SENSOR_RULES
}
VALID_SENSOR_NAMES: tuple[SensorName, ...] = tuple(SENSOR_RULES_BY_NAME.keys())


# Return one rule by sensor name so callers do not duplicate rule lookup logic.
def get_sensor_rule(sensor_name: SensorName) -> SensorRule:
    return SENSOR_RULES_BY_NAME[sensor_name]


# Split a slash-separated sensor_type value into validated sensor names.
def parse_sensor_type(sensor_type: str) -> tuple[SensorName, ...]:
    names = tuple(part.strip() for part in sensor_type.split("/") if part.strip())
    if not names:
        raise ValueError("sensor_type must contain at least one sensor name.")

    unknown_names = [
        name for name in names if name not in SENSOR_RULES_BY_NAME
    ]
    if unknown_names:
        raise ValueError(f"unknown sensor type(s): {', '.join(unknown_names)}")

    return names  # type: ignore[return-value]


# Return measurement fields that should be non-zero-capable for active sensors.
def get_active_measurement_fields(
    active_sensors: tuple[SensorName, ...],
) -> tuple[MeasurementField, ...]:
    return tuple(get_sensor_rule(sensor).measurement_field for sensor in active_sensors)


# Return measurement fields that must stay zero for a given active sensor set.
def get_inactive_measurement_fields(
    active_sensors: tuple[SensorName, ...],
) -> tuple[MeasurementField, ...]:
    active_fields = set(get_active_measurement_fields(active_sensors))
    return tuple(field for field in MEASUREMENT_FIELDS if field not in active_fields)


# Check whether one active sensor value is inside its inclusive valid range.
def is_value_in_active_range(sensor_name: SensorName, value: int | float) -> bool:
    rule = get_sensor_rule(sensor_name)
    return rule.min_value <= float(value) <= rule.max_value
