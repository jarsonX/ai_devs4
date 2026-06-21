# Shared data objects for the L17 windpower workflow.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# Store one decoded or raw Hub response.
@dataclass(frozen=True)
class ApiResponse:
    status_code: int
    payload: Any | None
    text: str


# Store one masked request and its full response for runtime logs.
@dataclass(frozen=True)
class LoggedExchange:
    request: dict[str, Any]
    response: ApiResponse


# Represent one weather forecast point from the Hub report.
@dataclass(frozen=True)
class WeatherPoint:
    timestamp: str
    wind_ms: float
    precipitation_mm: float
    temperature_c: float


# Represent parsed turbine documentation needed by the solver.
@dataclass(frozen=True)
class TurbineDocumentation:
    rated_power_kw: float
    cutoff_wind_ms: float
    min_operational_wind_ms: float
    pitch_yields: dict[int, float]


# Represent the power plant status relevant to scheduling.
@dataclass(frozen=True)
class PowerPlantReport:
    power_deficit_min_kw: float
    power_deficit_max_kw: float
    produced_power_kw: float


# Represent the turbine status relevant to scheduling.
@dataclass(frozen=True)
class TurbineReport:
    blade_pitch_angle_deg: int
    battery: str
    status: str


# Represent one unsigned schedule point.
@dataclass(frozen=True)
class ConfigPoint:
    timestamp: str
    start_date: str
    start_hour: str
    wind_ms: float
    pitch_angle: int
    turbine_mode: str
    reason: str


# Represent one signed schedule point ready for batch config.
@dataclass(frozen=True)
class SignedConfigPoint:
    point: ConfigPoint
    unlock_code: str


# Store the final high-level workflow result.
@dataclass(frozen=True)
class WorkflowResult:
    status: str
    run_log_path: str
    run_report_path: str
    final_response_path: str | None
    config_count: int
    flag_found: bool

    # Convert the result into JSON-safe output for CLI printing.
    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "run_log_path": self.run_log_path,
            "run_report_path": self.run_report_path,
            "final_response_path": self.final_response_path,
            "config_count": self.config_count,
            "flag_found": self.flag_found,
        }
