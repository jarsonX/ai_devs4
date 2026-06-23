# Shared data objects for the L18 Domatowo workflow.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# Store one decoded or raw Hub response.
@dataclass(frozen=True)
class ApiResponse:
    status_code: int
    payload: Any | None
    text: str


# Store one masked request and its matching Hub response.
@dataclass(frozen=True)
class LoggedExchange:
    sequence: int
    action: str
    request: dict[str, Any]
    response: ApiResponse


# Represent one map coordinate with zero-based indexes and Hub notation.
@dataclass(frozen=True, order=True)
class Field:
    row: int
    col: int

    # Convert this field to the Hub coordinate format, for example A6.
    def label(self) -> str:
        return f"{chr(ord('A') + self.col)}{self.row + 1}"


# Represent one connected high-block group to search.
@dataclass(frozen=True)
class TargetGroup:
    targets: tuple[Field, ...]


# Represent one transporter stop and the fields assigned to its scouts.
@dataclass(frozen=True)
class TransportPlan:
    spawn: Field
    stop: Field
    targets: tuple[Field, ...]
    passengers: int
    estimated_cost: int


# Store the Hub object fields the workflow needs.
@dataclass(frozen=True)
class Unit:
    object_id: str
    unit_type: str
    position: Field


# Store the final high-level workflow result.
@dataclass(frozen=True)
class WorkflowResult:
    status: str
    run_log_path: str
    run_report_path: str
    final_response_path: str | None
    inspected_fields: list[str]
    rescue_destination: str | None
    action_points_used: int | None
    action_points_left: int | None
    flag_found: bool

    # Convert the result into JSON-safe output for CLI printing.
    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "run_log_path": self.run_log_path,
            "run_report_path": self.run_report_path,
            "final_response_path": self.final_response_path,
            "inspected_fields": self.inspected_fields,
            "rescue_destination": self.rescue_destination,
            "action_points_used": self.action_points_used,
            "action_points_left": self.action_points_left,
            "flag_found": self.flag_found,
        }
