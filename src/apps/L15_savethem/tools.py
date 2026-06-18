# Narrow discovery tools and bounded toolbox for the L15 explorer agent.

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from openai.types.responses.function_tool_param import FunctionToolParam
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from src.apps.L15_savethem.api_client import CourseApiClient, LoggedExchange, build_payload_summary, parse_discovered_tools
from src.apps.L15_savethem.config import AppConfig
from src.apps.L15_savethem.models import ApiObservation, DiscoveredTool, ToolTraceEvent
from src.apps.L15_savethem.run_log import append_trace_event


REQUIRED_VEHICLE_MODES = ("walk", "horse", "car", "rocket")
ALLOWED_VALUES_PATTERN = re.compile(r"Allowed values:\s*(.+?)\.", re.IGNORECASE)


# Validate arguments for one discovery search through toolsearch.
class SearchToolsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=200)

    # Keep discovery prompts compact and intentional.
    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        return value.strip()


# Validate arguments for one discovered endpoint query.
class QueryToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(min_length=1, max_length=60)
    query: str = Field(min_length=1, max_length=200)

    # Keep tool names normalized before lookup.
    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, value: str) -> str:
        return value.strip()

    # Keep endpoint queries compact and intentional.
    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        return value.strip()


# Store the required observation ids for the four supported modes.
class VehicleObservationIds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    walk: str = Field(min_length=1, max_length=40)
    horse: str = Field(min_length=1, max_length=40)
    car: str = Field(min_length=1, max_length=40)
    rocket: str = Field(min_length=1, max_length=40)


# Validate the structured stop payload before exploration can finish.
class FinishExplorationArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "blocked"]
    destination_city: str = Field(default="", max_length=80)
    map_observation_id: str | None = Field(default=None, max_length=40)
    vehicle_observation_ids: VehicleObservationIds | None = None
    supporting_observation_ids: list[str] = Field(default_factory=list, max_length=12)
    reason: str = Field(min_length=1, max_length=400)
    unknowns: list[str] = Field(default_factory=list, max_length=12)

    # Keep optional text fields normalized before validation.
    @field_validator("destination_city", "reason")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return value.strip()

    # Keep uncertainty notes compact and non-empty.
    @field_validator("unknowns")
    @classmethod
    def validate_unknowns(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]

    # Keep support observation ids normalized before lookup.
    @field_validator("supporting_observation_ids")
    @classmethod
    def validate_ids(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


# Store one stable tool execution result for the agent loop.
@dataclass(frozen=True)
class ExplorerToolResult:
    tool_name: str
    ok: bool
    payload: dict[str, Any]

    # Convert the tool result into a JSON-ready dictionary.
    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "ok": self.ok,
            "payload": self.payload,
        }


# Build a strict OpenAI-compatible schema from one Pydantic model schema.
def build_openai_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    normalized_schema = dict(schema)

    if normalized_schema.get("type") == "object":
        properties = normalized_schema.get("properties", {})
        if isinstance(properties, dict):
            normalized_schema["properties"] = {
                key: build_openai_strict_schema(value) if isinstance(value, dict) else value
                for key, value in properties.items()
            }
            normalized_schema["required"] = list(properties.keys())
        normalized_schema["additionalProperties"] = False

    items = normalized_schema.get("items")
    if isinstance(items, dict):
        normalized_schema["items"] = build_openai_strict_schema(items)

    for keyword in ("anyOf", "allOf", "oneOf"):
        values = normalized_schema.get(keyword)
        if isinstance(values, list):
            normalized_schema[keyword] = [
                build_openai_strict_schema(value) if isinstance(value, dict) else value
                for value in values
            ]

    for defs_key in ("$defs", "definitions"):
        defs_value = normalized_schema.get(defs_key)
        if isinstance(defs_value, dict):
            normalized_schema[defs_key] = {
                key: build_openai_strict_schema(value) if isinstance(value, dict) else value
                for key, value in defs_value.items()
            }

    normalized_schema.pop("default", None)
    return normalized_schema


# Return the narrow tool schemas exposed to the explorer model.
def build_tool_definitions() -> list[FunctionToolParam]:
    return [
        cast(FunctionToolParam, {
            "type": "function",
            "name": "search_tools",
            "description": (
                "Search the unknown API environment through toolsearch. "
                "Use English queries only."
            ),
            "parameters": build_openai_strict_schema(SearchToolsArgs.model_json_schema()),
            "strict": True,
        }),
        cast(FunctionToolParam, {
            "type": "function",
            "name": "query_tool",
            "description": (
                "Query one previously discovered tool with an English query. "
                "Use this to test its contract and gather mission facts."
            ),
            "parameters": build_openai_strict_schema(QueryToolArgs.model_json_schema()),
            "strict": True,
        }),
        cast(FunctionToolParam, {
            "type": "function",
            "name": "finish_exploration",
            "description": (
                "Stop exploration as ready or blocked. "
                "When ready, point to the observation ids that ground the map, all four vehicle records, and the supporting notes."
            ),
            "parameters": build_openai_strict_schema(FinishExplorationArgs.model_json_schema()),
            "strict": True,
        }),
    ]


# Build one stable error result when tool execution fails.
def build_error_result(tool_name: str, error: Exception) -> ExplorerToolResult:
    return ExplorerToolResult(
        tool_name=tool_name,
        ok=False,
        payload={"error": str(error)},
    )


# This toolbox owns discovery state, observed responses, and finish validation.
class ExplorerToolbox:
    # Store app config, API client, and runtime state in one bounded toolbox.
    def __init__(
        self,
        config: AppConfig,
        api_client: CourseApiClient,
    ) -> None:
        self.config = config
        self.api_client = api_client
        self.discovered_tools: dict[str, DiscoveredTool] = {}
        self.observations: list[ApiObservation] = []
        self.tool_trace: list[ToolTraceEvent] = []
        self.tool_call_count = 0
        self.finished_payload: dict[str, Any] | None = None
        self._observation_sequence = 0
        self._trace_sequence = 0

    # Validate arguments, dispatch one supported tool, and trace the outcome.
    def dispatch_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ExplorerToolResult:
        self.tool_call_count += 1

        try:
            if tool_name == "search_tools":
                parsed_arguments = SearchToolsArgs.model_validate(arguments)
                result = self._search_tools(parsed_arguments)
            elif tool_name == "query_tool":
                parsed_arguments = QueryToolArgs.model_validate(arguments)
                result = self._query_tool(parsed_arguments)
            elif tool_name == "finish_exploration":
                parsed_arguments = FinishExplorationArgs.model_validate(arguments)
                result = self._finish_exploration(parsed_arguments)
            else:
                raise ValueError(f"Unsupported tool: {tool_name}")
        except ValidationError as error:
            result = build_error_result(
                tool_name,
                ValueError(f"Tool arguments failed validation: {error}"),
            )
        except Exception as error:
            result = build_error_result(tool_name, error)

        trace_event = ToolTraceEvent(
            sequence=self._next_trace_sequence(),
            tool_name=tool_name,
            arguments=arguments,
            result_ok=result.ok,
            payload=result.payload,
        )
        self.tool_trace.append(trace_event)
        append_trace_event(
            self.config.paths.trace_log_file,
            "tool_call",
            trace_event.to_dict(),
        )
        return result

    # Search the unknown environment through toolsearch and store discovered tools.
    def _search_tools(self, arguments: SearchToolsArgs) -> ExplorerToolResult:
        exchange = self.api_client.search_tools(arguments.query)
        observation = self._store_observation(
            tool_name="toolsearch",
            query=arguments.query,
            exchange=exchange,
        )
        discovered_tools = parse_discovered_tools(exchange.response.payload)
        for tool in discovered_tools:
            self.discovered_tools[tool.name] = tool

        payload = {
            "observation_id": observation.observation_id,
            "query": arguments.query,
            "discovered_tools": [tool.to_dict() for tool in discovered_tools],
            "known_tools": [tool.to_dict() for tool in sorted(self.discovered_tools.values(), key=lambda item: item.name)],
            "response_summary": observation.summary,
            "recovery_hints": self._build_search_recovery_hints(),
        }
        return ExplorerToolResult(
            tool_name="search_tools",
            ok=True,
            payload=payload,
        )

    # Query one discovered tool and store the observed endpoint response.
    def _query_tool(self, arguments: QueryToolArgs) -> ExplorerToolResult:
        tool = self.discovered_tools.get(arguments.tool_name)
        if tool is None:
            known_tool_names = sorted(self.discovered_tools.keys())
            raise ValueError(
                "Unknown tool_name. Use search_tools first or choose one of: "
                + ", ".join(known_tool_names)
            )

        exchange = self.api_client.query_tool(tool, arguments.query)
        observation = self._store_observation(
            tool_name=tool.name,
            query=arguments.query,
            exchange=exchange,
        )
        payload = {
            "observation_id": observation.observation_id,
            "tool_name": tool.name,
            "query": arguments.query,
            "ok": observation.ok,
            "response_summary": observation.summary,
            "recovery_hints": self._build_recovery_hints(tool, arguments.query, observation),
        }
        return ExplorerToolResult(
            tool_name="query_tool",
            ok=True,
            payload=payload,
        )

    # Validate the finish payload before exploration can stop.
    def _finish_exploration(self, arguments: FinishExplorationArgs) -> ExplorerToolResult:
        normalized_payload = {
            "status": arguments.status,
            "destination_city": arguments.destination_city or None,
            "map_observation_id": arguments.map_observation_id,
            "vehicle_observation_ids": (
                arguments.vehicle_observation_ids.model_dump()
                if arguments.vehicle_observation_ids is not None
                else {}
            ),
            "supporting_observation_ids": arguments.supporting_observation_ids,
            "reason": arguments.reason,
            "unknowns": arguments.unknowns,
            "finished": True,
        }

        if arguments.status == "ready":
            if not arguments.destination_city:
                raise ValueError("Ready exploration requires destination_city.")
            if not arguments.map_observation_id:
                raise ValueError("Ready exploration requires map_observation_id.")
            if arguments.vehicle_observation_ids is None:
                raise ValueError("Ready exploration requires all vehicle observation ids.")
            if not arguments.supporting_observation_ids:
                raise ValueError("Ready exploration requires supporting note observations.")

            self._validate_map_observation(arguments.map_observation_id)
            for mode in REQUIRED_VEHICLE_MODES:
                observation_id = getattr(arguments.vehicle_observation_ids, mode)
                self._validate_vehicle_observation(observation_id, expected_mode=mode)
            for observation_id in arguments.supporting_observation_ids:
                self._require_observation(observation_id)

        self.finished_payload = normalized_payload
        return ExplorerToolResult(
            tool_name="finish_exploration",
            ok=True,
            payload=normalized_payload,
        )

    # Return one observed response by id or fail with a clear message.
    def _require_observation(self, observation_id: str) -> ApiObservation:
        for observation in self.observations:
            if observation.observation_id == observation_id:
                return observation
        raise ValueError(f"Unknown observation id: {observation_id}")

    # Check that the chosen map observation came from the maps endpoint.
    def _validate_map_observation(self, observation_id: str) -> None:
        observation = self._require_observation(observation_id)
        if observation.tool_name != "maps" or not observation.ok:
            raise ValueError("map_observation_id must point to a successful maps observation.")

    # Check that the chosen vehicle observation came from wehicles and matches the mode.
    def _validate_vehicle_observation(self, observation_id: str, *, expected_mode: str) -> None:
        observation = self._require_observation(observation_id)
        if observation.tool_name != "wehicles" or not observation.ok:
            raise ValueError(
                f"Vehicle observation for {expected_mode} must point to a successful wehicles observation."
            )
        payload = observation.response.payload
        observed_name = str(payload.get("name", "")).strip() if isinstance(payload, dict) else ""
        if observed_name != expected_mode:
            raise ValueError(
                f"Vehicle observation {observation_id} returned {observed_name!r}, expected {expected_mode!r}."
            )

    # Store one observation, its cache artifact, and a trace event.
    def _store_observation(
        self,
        *,
        tool_name: str,
        query: str,
        exchange: LoggedExchange,
    ) -> ApiObservation:
        self._observation_sequence += 1
        observation_id = f"obs-{self._observation_sequence:03d}"
        cache_file = self._write_observation_cache(
            observation_id=observation_id,
            tool_name=tool_name,
            query=query,
            exchange=exchange,
        )
        summary = build_payload_summary(
            exchange.response.payload,
            max_chars=self.config.runtime.max_tool_result_chars,
        )
        observation = ApiObservation(
            observation_id=observation_id,
            tool_name=tool_name,
            query=query,
            ok=exchange.response.status_code < 400,
            response=exchange.response,
            cache_file=str(cache_file.relative_to(self.config.paths.repo_root)),
            summary=summary,
        )
        self.observations.append(observation)
        append_trace_event(
            self.config.paths.trace_log_file,
            "observation",
            observation.to_dict(),
        )
        return observation

    # Persist one raw exchange under runtime cache for later debugging.
    def _write_observation_cache(
        self,
        *,
        observation_id: str,
        tool_name: str,
        query: str,
        exchange: LoggedExchange,
    ) -> Path:
        file_path = self.config.paths.cache_dir / f"{observation_id}_{tool_name}.json"
        payload = {
            "observation_id": observation_id,
            "tool_name": tool_name,
            "query": query,
            "request": exchange.request,
            "response": exchange.response.to_dict(),
        }
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        return file_path

    # Return the next stable trace sequence number.
    def _next_trace_sequence(self) -> int:
        self._trace_sequence += 1
        return self._trace_sequence

    # Build concrete search follow-up hints from the currently known tool set.
    def _build_search_recovery_hints(self) -> list[str]:
        known_tool_names = set(self.discovered_tools.keys())
        hints: list[str] = []
        if "maps" not in known_tool_names:
            hints.append("Search for map or city terrain tools if the destination map is still missing.")
        if "wehicles" not in known_tool_names:
            hints.append("Search again with queries focused on vehicles, travel modes, car, horse, rocket, and walk.")
        if "books" not in known_tool_names:
            hints.append("Search again with queries focused on books, notes, movement rules, terrain markers, water, rocks, trees, and dismount.")
        if not hints:
            hints.append("You have already discovered the core tools. Use query_tool to learn their exact request contracts.")
        return hints

    # Build concrete next-step hints from observed success and failure patterns.
    def _build_recovery_hints(
        self,
        tool: DiscoveredTool,
        query: str,
        observation: ApiObservation,
    ) -> list[str]:
        hints: list[str] = []
        payload = observation.response.payload
        message = ""
        if isinstance(payload, dict):
            message = str(payload.get("message", "")).strip()

        if tool.name == "maps":
            if observation.ok:
                hints.append(
                    "The maps endpoint accepted this request. Reuse the exact city-name-only pattern for map retrieval."
                )
            elif "such a city" in message.lower():
                hints.append(
                    "The maps endpoint likely expects only the destination city name, for example 'Skolwin', with no extra words."
                )

        if tool.name == "wehicles":
            if observation.ok and query in REQUIRED_VEHICLE_MODES:
                hints.append(
                    "The wehicles endpoint accepted an exact mode name. Query the remaining modes by sending only one allowed value."
                )
            elif "allowed values" in message.lower():
                allowed_values_match = ALLOWED_VALUES_PATTERN.search(message)
                if allowed_values_match is not None:
                    allowed_values = [item.strip() for item in allowed_values_match.group(1).split(",") if item.strip()]
                    hints.append(
                        "The wehicles endpoint rejected a descriptive query and revealed exact allowed values: "
                        + ", ".join(allowed_values)
                        + "."
                    )
                    hints.append(
                        "Retry wehicles using one exact allowed value only, such as 'walk' or 'rocket'."
                    )

        if tool.name == "books":
            if observation.ok:
                hints.append(
                    "The books endpoint behaves like full-text search. Use short keyword queries for rules, commands, water, rocks, trees, and dismount."
                )

        if tool.name == "toolsearch":
            if isinstance(payload, dict) and isinstance(payload.get("tools"), list):
                tool_names = [
                    str(item.get("name", "")).strip()
                    for item in payload["tools"]
                    if isinstance(item, dict)
                ]
                if "books" not in tool_names:
                    hints.append(
                        "If rule-oriented tools are still missing, run another search_tools query focused on notes, books, movement rules, or terrain markers."
                    )

        return hints

    # Build a deterministic blocked payload when the model never finishes properly.
    def build_fallback_finish_payload(
        self,
        *,
        reason: str,
    ) -> dict[str, Any]:
        return {
            "status": "blocked",
            "destination_city": None,
            "map_observation_id": None,
            "vehicle_observation_ids": {},
            "supporting_observation_ids": [],
            "reason": reason,
            "unknowns": [],
            "finished": False,
        }

    # Return compact runtime state for reports and local debugging.
    def build_runtime_summary(self) -> dict[str, Any]:
        return {
            "discovered_tools": [
                tool.to_dict()
                for tool in sorted(self.discovered_tools.values(), key=lambda item: item.name)
            ],
            "observations": [observation.to_dict() for observation in self.observations],
            "tool_trace": [event.to_dict() for event in self.tool_trace],
            "tool_call_count": self.tool_call_count,
            "finished_payload": self.finished_payload,
            "trace_log_file": str(self.config.paths.trace_log_file.relative_to(self.config.paths.repo_root)),
        }
