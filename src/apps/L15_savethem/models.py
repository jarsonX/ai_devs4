# Shared models for the L15_savethem workflow.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Store one discovered external tool together with the search metadata.
@dataclass(frozen=True)
class DiscoveredTool:
    name: str
    url: str
    description: str
    parameter: str
    score: int | None = None
    matched_keywords: tuple[str, ...] = ()

    # Convert the tool into a JSON-ready dictionary.
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "parameter": self.parameter,
            "score": self.score,
            "matched_keywords": list(self.matched_keywords),
        }


# Store one API response without losing non-JSON fallback text.
@dataclass(frozen=True)
class ApiResponse:
    status_code: int
    payload: Any
    text: str

    # Convert the response into a JSON-ready dictionary.
    def to_dict(self) -> dict[str, Any]:
        return {
            "status_code": self.status_code,
            "payload": self.payload,
            "text": self.text,
        }


# Store one observed discovery or endpoint exchange.
@dataclass(frozen=True)
class ApiObservation:
    observation_id: str
    tool_name: str
    query: str
    ok: bool
    response: ApiResponse
    cache_file: str
    summary: dict[str, Any]

    # Convert the observation into a JSON-ready dictionary.
    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "tool_name": self.tool_name,
            "query": self.query,
            "ok": self.ok,
            "response": self.response.to_dict(),
            "cache_file": self.cache_file,
            "summary": self.summary,
        }


# Store one validated vehicle resource profile.
@dataclass(frozen=True)
class VehicleSpec:
    mode: str
    fuel_per_move: float
    food_per_move: float
    note: str

    # Convert the vehicle into a JSON-ready dictionary.
    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "fuel_per_move": self.fuel_per_move,
            "food_per_move": self.food_per_move,
            "note": self.note,
        }


# Store one normalized mission-knowledge snapshot derived from exploration.
@dataclass(frozen=True)
class MissionKnowledge:
    destination_city: str
    map_rows: tuple[str, ...]
    start_row: int
    start_col: int
    goal_row: int
    goal_col: int
    vehicles: dict[str, VehicleSpec]
    commands: tuple[str, ...]
    water_allowed_modes: tuple[str, ...]
    powered_modes: tuple[str, ...]
    rock_blocks_all: bool
    tree_additional_fuel: float
    resources_consumed_on_move: bool
    vehicle_selected_at_departure: bool
    dismount_allowed: bool
    note_ids_used: tuple[str, ...] = ()

    # Convert the knowledge object into a JSON-ready dictionary.
    def to_dict(self) -> dict[str, Any]:
        return {
            "destination_city": self.destination_city,
            "map_rows": list(self.map_rows),
            "start_row": self.start_row,
            "start_col": self.start_col,
            "goal_row": self.goal_row,
            "goal_col": self.goal_col,
            "vehicles": {
                mode: vehicle.to_dict()
                for mode, vehicle in sorted(self.vehicles.items())
            },
            "commands": list(self.commands),
            "water_allowed_modes": list(self.water_allowed_modes),
            "powered_modes": list(self.powered_modes),
            "rock_blocks_all": self.rock_blocks_all,
            "tree_additional_fuel": self.tree_additional_fuel,
            "resources_consumed_on_move": self.resources_consumed_on_move,
            "vehicle_selected_at_departure": self.vehicle_selected_at_departure,
            "dismount_allowed": self.dismount_allowed,
            "note_ids_used": list(self.note_ids_used),
        }


# Store one route candidate with its commands and resource summary.
@dataclass(frozen=True)
class RoutePlan:
    commands: tuple[str, ...]
    final_row: int
    final_col: int
    remaining_fuel: float
    remaining_food: float
    fuel_spent: float
    food_spent: float
    reached_goal: bool
    visited_positions: tuple[tuple[int, int], ...] = ()

    # Convert the route plan into a JSON-ready dictionary.
    def to_dict(self) -> dict[str, Any]:
        return {
            "commands": list(self.commands),
            "final_row": self.final_row,
            "final_col": self.final_col,
            "remaining_fuel": self.remaining_fuel,
            "remaining_food": self.remaining_food,
            "fuel_spent": self.fuel_spent,
            "food_spent": self.food_spent,
            "reached_goal": self.reached_goal,
            "visited_positions": [list(position) for position in self.visited_positions],
        }


# Store the final workflow result together with report pointers.
@dataclass(frozen=True)
class WorkflowResult:
    status: str
    exploration_status: str
    knowledge: MissionKnowledge | None
    route_plan: RoutePlan | None
    report_path: str | None
    model_calls_used: int
    tool_calls_used: int
    submission_response: dict[str, Any] | None = None
    stop_reason: str | None = None
    route_blocker: str | None = None

    # Convert the result into a JSON-ready dictionary.
    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "exploration_status": self.exploration_status,
            "knowledge": self.knowledge.to_dict() if self.knowledge else None,
            "route_plan": self.route_plan.to_dict() if self.route_plan else None,
            "report_path": self.report_path,
            "model_calls_used": self.model_calls_used,
            "tool_calls_used": self.tool_calls_used,
            "submission_response": self.submission_response,
            "stop_reason": self.stop_reason,
            "route_blocker": self.route_blocker,
        }


# Store one turn-level tool trace for JSONL logs and final reports.
@dataclass(frozen=True)
class ToolTraceEvent:
    sequence: int
    tool_name: str
    arguments: dict[str, Any]
    result_ok: bool
    payload: dict[str, Any]

    # Convert the event into a JSON-ready dictionary.
    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result_ok": self.result_ok,
            "payload": self.payload,
        }


# Store the result of the exploration loop before deterministic knowledge parsing.
@dataclass(frozen=True)
class ExplorationResult:
    status: str
    destination_city: str | None
    map_observation_id: str | None
    vehicle_observation_ids: dict[str, str]
    supporting_observation_ids: tuple[str, ...]
    reason: str
    unknowns: tuple[str, ...]
    observations: tuple[ApiObservation, ...]
    discovered_tools: tuple[DiscoveredTool, ...]
    tool_trace: tuple[ToolTraceEvent, ...]
    model_calls_used: int
    tool_calls_used: int
    stop_reason: str
    raw_final_text: str | None = None
    runtime_summary: dict[str, Any] = field(default_factory=dict)

    # Convert the exploration result into a JSON-ready dictionary.
    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "destination_city": self.destination_city,
            "map_observation_id": self.map_observation_id,
            "vehicle_observation_ids": dict(self.vehicle_observation_ids),
            "supporting_observation_ids": list(self.supporting_observation_ids),
            "reason": self.reason,
            "unknowns": list(self.unknowns),
            "observations": [observation.to_dict() for observation in self.observations],
            "discovered_tools": [tool.to_dict() for tool in self.discovered_tools],
            "tool_trace": [event.to_dict() for event in self.tool_trace],
            "model_calls_used": self.model_calls_used,
            "tool_calls_used": self.tool_calls_used,
            "stop_reason": self.stop_reason,
            "raw_final_text": self.raw_final_text,
            "runtime_summary": self.runtime_summary,
        }

