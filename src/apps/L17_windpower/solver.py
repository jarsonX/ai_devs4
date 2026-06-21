# Deterministic scheduling logic for the L17 windpower task.

from __future__ import annotations

import re
from typing import Any

from src.apps.L17_windpower.models import (
    ConfigPoint,
    PowerPlantReport,
    TurbineDocumentation,
    TurbineReport,
    WeatherPoint,
)


POWER_RANGE_PATTERN = re.compile(r"(?P<low>\d+(?:\.\d+)?)(?:\s*-\s*(?P<high>\d+(?:\.\d+)?))?")


# Parse one timestamp into the date and hour fields expected by config APIs.
def split_timestamp(timestamp: str) -> tuple[str, str]:
    date_part, hour_part = timestamp.split(" ", 1)
    hour = hour_part.split(":", 1)[0]
    return date_part, f"{int(hour):02d}:00:00"


# Parse documentation fields needed by the solver.
def parse_documentation(payload: dict[str, Any]) -> TurbineDocumentation:
    pitch_yields: dict[int, float] = {}
    for item in payload.get("pitchAngleYieldPercent", []):
        angle = int(item["pitchAngleDeg"])
        yield_percent = float(str(item["yieldPercent"]).replace("%", ""))
        pitch_yields[angle] = yield_percent / 100.0

    return TurbineDocumentation(
        rated_power_kw=float(payload["ratedPowerKw"]),
        cutoff_wind_ms=float(payload["safety"]["cutoffWindMs"]),
        min_operational_wind_ms=float(payload["safety"]["minOperationalWindMs"]),
        pitch_yields=pitch_yields,
    )


# Parse weather forecast rows into typed weather points.
def parse_weather(payload: dict[str, Any]) -> list[WeatherPoint]:
    points: list[WeatherPoint] = []
    for item in payload.get("forecast", []):
        points.append(
            WeatherPoint(
                timestamp=str(item["timestamp"]),
                wind_ms=float(item["windMs"]),
                precipitation_mm=float(item.get("precipitationMm", 0)),
                temperature_c=float(item.get("temperatureC", 0)),
            )
        )
    return points


# Parse the power deficit range from the power plant report.
def parse_powerplant_report(payload: dict[str, Any]) -> PowerPlantReport:
    raw_deficit = str(payload.get("powerDeficitKw", "0"))
    match = POWER_RANGE_PATTERN.search(raw_deficit)
    if not match:
        raise ValueError(f"Cannot parse powerDeficitKw: {raw_deficit!r}.")

    low = float(match.group("low"))
    high = float(match.group("high") or match.group("low"))
    return PowerPlantReport(
        power_deficit_min_kw=low,
        power_deficit_max_kw=high,
        produced_power_kw=float(payload.get("producedPowerKw", 0)),
    )


# Parse the turbine report fields relevant to safety checks.
def parse_turbine_report(payload: dict[str, Any]) -> TurbineReport:
    return TurbineReport(
        blade_pitch_angle_deg=int(payload.get("bladePitchAngleDeg", 0)),
        battery=str(payload.get("battery", "")),
        status=str(payload.get("status", "")),
    )


# Return the documented wind yield range for one wind speed.
def wind_yield_range(wind_ms: float, documentation: TurbineDocumentation) -> tuple[float, float]:
    if wind_ms < documentation.min_operational_wind_ms:
        return 0.0, 0.0
    if wind_ms > documentation.cutoff_wind_ms:
        return 0.0, 0.0
    if wind_ms >= 11:
        return 1.0, 1.0
    if wind_ms >= 9:
        return 0.90, 1.00
    if wind_ms >= 7:
        return 0.60, 0.70
    if wind_ms >= 5.5:
        return 0.30, 0.40
    return 0.10, 0.15


# Estimate generated power range for a weather point and pitch angle.
def estimate_power_range_kw(
    point: WeatherPoint,
    documentation: TurbineDocumentation,
    *,
    pitch_angle: int,
) -> tuple[float, float]:
    wind_low, wind_high = wind_yield_range(point.wind_ms, documentation)
    pitch_yield = documentation.pitch_yields.get(pitch_angle, 0.0)
    return (
        documentation.rated_power_kw * wind_low * pitch_yield,
        documentation.rated_power_kw * wind_high * pitch_yield,
    )


# Return whether a generated power range can cover the deficit range.
def covers_deficit(power_range: tuple[float, float], powerplant: PowerPlantReport) -> bool:
    low, high = power_range
    return high >= powerplant.power_deficit_min_kw and low <= powerplant.power_deficit_max_kw


# Build one config point from a timestamp and scheduling parameters.
def build_config_point(
    *,
    timestamp: str,
    wind_ms: float,
    pitch_angle: int,
    turbine_mode: str,
    reason: str,
) -> ConfigPoint:
    start_date, start_hour = split_timestamp(timestamp)
    return ConfigPoint(
        timestamp=f"{start_date} {start_hour}",
        start_date=start_date,
        start_hour=start_hour,
        wind_ms=wind_ms,
        pitch_angle=pitch_angle,
        turbine_mode=turbine_mode,
        reason=reason,
    )


# Choose the earliest production point that can cover the power deficit.
def select_production_point(
    weather: list[WeatherPoint],
    documentation: TurbineDocumentation,
    powerplant: PowerPlantReport,
) -> ConfigPoint:
    target_midpoint = (powerplant.power_deficit_min_kw + powerplant.power_deficit_max_kw) / 2
    candidates: list[tuple[str, float, WeatherPoint, int]] = []
    for point in weather:
        if point.wind_ms > documentation.cutoff_wind_ms:
            continue
        for pitch_angle in (0, 45):
            power_range = estimate_power_range_kw(point, documentation, pitch_angle=pitch_angle)
            if covers_deficit(power_range, powerplant):
                generated_midpoint = (power_range[0] + power_range[1]) / 2
                candidates.append(
                    (
                        point.timestamp,
                        abs(generated_midpoint - target_midpoint),
                        point,
                        pitch_angle,
                    )
                )

    if not candidates:
        raise ValueError("No production weather point can cover the power deficit.")

    _, _, selected, pitch_angle = sorted(candidates, key=lambda item: (item[0], item[1]))[0]
    return build_config_point(
        timestamp=selected.timestamp,
        wind_ms=selected.wind_ms,
        pitch_angle=pitch_angle,
        turbine_mode="production",
        reason="cover_power_deficit",
    )


# Convert live reports into the minimal safe schedule.
def solve_schedule(
    *,
    documentation: TurbineDocumentation,
    weather: list[WeatherPoint],
    powerplant: PowerPlantReport,
    turbine: TurbineReport,
) -> list[ConfigPoint]:
    if "correct" not in turbine.status.lower() and "operating" not in turbine.status.lower():
        raise ValueError(f"Turbine status does not look operational: {turbine.status!r}.")

    shutdown_points = [
        build_config_point(
            timestamp=point.timestamp,
            wind_ms=point.wind_ms,
            pitch_angle=90,
            turbine_mode="idle",
            reason="storm_shutdown",
        )
        for point in weather
        if point.wind_ms > documentation.cutoff_wind_ms
    ]
    production_point = select_production_point(weather, documentation, powerplant)

    unique: dict[str, ConfigPoint] = {}
    for point in [*shutdown_points, production_point]:
        unique[point.timestamp] = point

    return [unique[key] for key in sorted(unique)]
