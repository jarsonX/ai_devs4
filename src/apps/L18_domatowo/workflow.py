# Live Hub orchestration for the L18 Domatowo workflow.

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

from src.apps.L18_domatowo.api_client import DomatowoApiClient
from src.apps.L18_domatowo.config import AppConfig, ensure_runtime_directories
from src.apps.L18_domatowo.models import Field, LoggedExchange, Unit, WorkflowResult
from src.apps.L18_domatowo.planner import (
    build_transport_plans,
    extract_grid,
    manhattan_distance,
    parse_field_label,
)
from src.apps.L18_domatowo.run_log import RunLog, append_event, create_run_log


# Write one JSON artifact into the output directory.
def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2, sort_keys=True)


# Serialize one logged exchange for runtime storage.
def exchange_to_dict(exchange: LoggedExchange) -> dict[str, Any]:
    return {
        "sequence": exchange.sequence,
        "action": exchange.action,
        "request": exchange.request,
        "response": {
            "status_code": exchange.response.status_code,
            "payload": exchange.response.payload,
            "text": exchange.response.text,
        },
    }


# Send an action, log the exchange, and return it to the caller.
def call_and_log(
    client: DomatowoApiClient,
    run_log: RunLog,
    *,
    event: str,
    secret_values: list[str],
    call: Any,
) -> LoggedExchange:
    exchange = call()
    append_event(
        run_log,
        event=event,
        data=exchange_to_dict(exchange),
        secret_values=secret_values,
    )
    return exchange


# Normalize text so Polish and English result phrases can be matched safely.
def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return without_marks.lower()


# Detect whether a Hub payload contains a FLAG.
def contains_flag(value: Any) -> bool:
    serialized = json.dumps(value, ensure_ascii=False)
    return "FLAG{" in serialized or "{FLG:" in serialized


# Detect positive survivor confirmation in one log or response object.
def survivor_confirmed_in_item(value: Any) -> bool:
    normalized = normalize_text(json.dumps(value, ensure_ascii=False))
    negative_phrases = (
        "nie znaleziono",
        "nie ma",
        "brak",
        "not found",
        "no human",
        "nothing",
        "empty",
        "negative",
    )
    if any(phrase in normalized for phrase in negative_phrases):
        return False

    positive_phrases = (
        "znaleziono",
        "odnaleziono",
        "potwierdzon",
        "osoba potwierdzona",
        "czlowiek",
        "partyzant",
        "survivor",
        "human confirmed",
        "found human",
        "evacuation ready",
        "namierzyc",
        "udalo sie",
    )
    return any(phrase in normalized for phrase in positive_phrases)


# Detect positive survivor confirmation while avoiding old negative logs.
def survivor_confirmed(value: Any) -> bool:
    if isinstance(value, dict) and isinstance(value.get("logs"), list):
        return any(survivor_confirmed_in_item(item) for item in value["logs"])
    return survivor_confirmed_in_item(value)


# Return the confirmed field from Hub logs when a prior inspection found the survivor.
def confirmed_field_from_logs(value: Any) -> Field | None:
    if not isinstance(value, dict) or not isinstance(value.get("logs"), list):
        return None
    for item in value["logs"]:
        if not isinstance(item, dict) or not survivor_confirmed_in_item(item):
            continue
        raw_field = item.get("field")
        if isinstance(raw_field, str):
            return parse_field_label(raw_field)
    return None


# Extract a list payload from the common Hub response shapes.
def extract_list(payload: Any, key: str) -> list[Any]:
    if isinstance(payload, dict) and isinstance(payload.get(key), list):
        return payload[key]
    return []


# Parse a unit position field from the object shape returned by Hub.
def parse_unit_position(raw_unit: dict[str, Any]) -> Field | None:
    for key in ("position", "field", "where", "location"):
        value = raw_unit.get(key)
        if isinstance(value, str):
            try:
                return parse_field_label(value)
            except ValueError:
                pass
        if isinstance(value, dict):
            for nested_key in ("field", "label", "coordinate", "position"):
                nested = value.get(nested_key)
                if isinstance(nested, str):
                    try:
                        return parse_field_label(nested)
                    except ValueError:
                        pass
    x_value = raw_unit.get("x", raw_unit.get("col"))
    y_value = raw_unit.get("y", raw_unit.get("row"))
    if isinstance(x_value, int) and isinstance(y_value, int):
        return Field(row=y_value - 1, col=x_value - 1)
    return None


# Parse known units from the Hub object list.
def parse_units(payload: Any) -> list[Unit]:
    units: list[Unit] = []
    for raw_unit in extract_list(payload, "objects"):
        if not isinstance(raw_unit, dict):
            continue
        object_id = ""
        for key in ("hash", "id", "object", "identifier"):
            if raw_unit.get(key):
                object_id = str(raw_unit[key])
                break
        unit_type = str(
            raw_unit.get("type", raw_unit.get("typ", raw_unit.get("kind", "")))
        ).lower()
        position = parse_unit_position(raw_unit)
        if object_id and unit_type and position is not None:
            units.append(Unit(object_id=object_id, unit_type=unit_type, position=position))
    return units


# Select a newly created transporter that is not yet known.
def find_new_transporter(before: list[Unit], after: list[Unit]) -> Unit:
    before_ids = {unit.object_id for unit in before}
    candidates = [
        unit
        for unit in after
        if unit.object_id not in before_ids and "transport" in unit.unit_type
    ]
    if candidates:
        return candidates[0]
    transporters = [unit for unit in after if "transport" in unit.unit_type]
    if not transporters:
        raise ValueError("Hub did not return a transporter object.")
    return transporters[-1]


# Select scouts that appeared after a dismount action.
def find_new_scouts(before: list[Unit], after: list[Unit], expected_count: int) -> list[Unit]:
    before_ids = {unit.object_id for unit in before}
    candidates = [
        unit
        for unit in after
        if unit.object_id not in before_ids and "scout" in unit.unit_type
    ]
    if len(candidates) < expected_count:
        all_scouts = [unit for unit in after if "scout" in unit.unit_type]
        candidates = all_scouts[-expected_count:]
    if len(candidates) < expected_count:
        raise ValueError("Hub did not return enough dismounted scout objects.")
    return candidates[:expected_count]


# Return the closest scout-target pair for the next inspection move.
def choose_next_assignment(
    scout_positions: dict[str, Field],
    targets: set[Field],
) -> tuple[str, Field]:
    best: tuple[int, str, Field] | None = None
    for scout_id, position in scout_positions.items():
        for target in targets:
            candidate = (manhattan_distance(position, target), scout_id, target)
            if best is None or candidate < best:
                best = candidate
    if best is None:
        raise ValueError("No scout-target assignment is available.")
    _, scout_id, target = best
    return scout_id, target


# Read action point usage from the expenses payload when available.
def parse_expense_totals(payload: Any) -> tuple[int | None, int | None]:
    if not isinstance(payload, dict):
        return None, None
    used = payload.get("action_points_used")
    left = payload.get("action_points_left")
    return (
        used if isinstance(used, int) else None,
        left if isinstance(left, int) else None,
    )


# Search a group of target fields with the scouts assigned to that group.
def inspect_group(
    client: DomatowoApiClient,
    run_log: RunLog,
    *,
    scouts: list[Unit],
    targets: tuple[Field, ...],
    inspected_fields: list[str],
    secret_values: list[str],
) -> Field | None:
    scout_positions = {scout.object_id: scout.position for scout in scouts}
    remaining_targets = set(targets)

    while remaining_targets:
        scout_id, target = choose_next_assignment(scout_positions, remaining_targets)
        if scout_positions[scout_id] != target:
            call_and_log(
                client,
                run_log,
                event="move_scout",
                secret_values=secret_values,
                call=lambda scout_id=scout_id, target=target: client.move(
                    scout_id,
                    target.label(),
                ),
            )
            scout_positions[scout_id] = target

        inspect_exchange = call_and_log(
            client,
            run_log,
            event="inspect",
            secret_values=secret_values,
            call=lambda scout_id=scout_id: client.inspect(scout_id),
        )
        inspected_fields.append(target.label())

        logs_exchange = call_and_log(
            client,
            run_log,
            event="get_logs_after_inspect",
            secret_values=secret_values,
            call=client.get_logs,
        )
        if survivor_confirmed(inspect_exchange.response.payload) or survivor_confirmed(
            logs_exchange.response.payload
        ):
            return target

        remaining_targets.remove(target)

    return None


# Run the real Domatowo operation through the Hub API.
def run_domatowo_workflow(
    config: AppConfig,
    *,
    reset_board: bool = True,
) -> WorkflowResult:
    if config.hub is None:
        raise ValueError("Hub config is required for submit runs.")

    ensure_runtime_directories(config.paths)
    run_log = create_run_log(config.paths.logs_dir)
    secret_values = [config.hub.api_key]
    client = DomatowoApiClient(
        config.hub,
        timeout_seconds=config.runtime.request_timeout_seconds,
        max_requests=config.runtime.max_requests,
    )

    if reset_board:
        call_and_log(
            client,
            run_log,
            event="reset",
            secret_values=secret_values,
            call=client.reset,
        )

    map_exchange = call_and_log(
        client,
        run_log,
        event="get_map",
        secret_values=secret_values,
        call=client.get_map,
    )
    cost_exchange = call_and_log(
        client,
        run_log,
        event="action_cost",
        secret_values=secret_values,
        call=client.action_cost,
    )

    grid = extract_grid(map_exchange.response.payload or {})
    plans = build_transport_plans(
        grid,
        transporter_limit=config.runtime.transporter_limit,
        scout_limit=config.runtime.scout_limit,
    )
    append_event(
        run_log,
        event="transport_plan",
        data={
            "plans": [
                {
                    "spawn": plan.spawn.label(),
                    "stop": plan.stop.label(),
                    "targets": [target.label() for target in plan.targets],
                    "passengers": plan.passengers,
                    "estimated_cost": plan.estimated_cost,
                }
                for plan in plans
            ],
            "cost_contract": cost_exchange.response.payload,
        },
        secret_values=secret_values,
    )

    inspected_fields: list[str] = []
    rescue_destination: Field | None = None
    final_exchange: LoggedExchange | None = None

    if not reset_board:
        existing_logs_exchange = call_and_log(
            client,
            run_log,
            event="get_existing_logs",
            secret_values=secret_values,
            call=client.get_logs,
        )
        rescue_destination = confirmed_field_from_logs(
            existing_logs_exchange.response.payload
        )
        if rescue_destination is not None:
            final_exchange = call_and_log(
                client,
                run_log,
                event="call_helicopter_from_existing_logs",
                secret_values=secret_values,
                call=lambda rescue_destination=rescue_destination: client.call_helicopter(
                    rescue_destination.label()
                ),
            )

    if final_exchange is None:
        for plan in plans:
            objects_before_create = parse_units(
                call_and_log(
                    client,
                    run_log,
                    event="get_objects_before_create",
                    secret_values=secret_values,
                    call=client.get_objects,
                ).response.payload
            )
            call_and_log(
                client,
                run_log,
                event="create_transporter",
                secret_values=secret_values,
                call=lambda plan=plan: client.create_transporter(plan.passengers),
            )
            objects_after_create = parse_units(
                call_and_log(
                    client,
                    run_log,
                    event="get_objects_after_create",
                    secret_values=secret_values,
                    call=client.get_objects,
                ).response.payload
            )
            transporter = find_new_transporter(objects_before_create, objects_after_create)

            call_and_log(
                client,
                run_log,
                event="move_transporter",
                secret_values=secret_values,
                call=lambda transporter=transporter, plan=plan: client.move(
                    transporter.object_id,
                    plan.stop.label(),
                ),
            )
            objects_before_dismount = parse_units(
                call_and_log(
                    client,
                    run_log,
                    event="get_objects_before_dismount",
                    secret_values=secret_values,
                    call=client.get_objects,
                ).response.payload
            )
            call_and_log(
                client,
                run_log,
                event="dismount",
                secret_values=secret_values,
                call=lambda transporter=transporter, plan=plan: client.dismount(
                    transporter.object_id,
                    plan.passengers,
                ),
            )
            objects_after_dismount = parse_units(
                call_and_log(
                    client,
                    run_log,
                    event="get_objects_after_dismount",
                    secret_values=secret_values,
                    call=client.get_objects,
                ).response.payload
            )
            scouts = find_new_scouts(
                objects_before_dismount,
                objects_after_dismount,
                plan.passengers,
            )

            rescue_destination = inspect_group(
                client,
                run_log,
                scouts=scouts,
                targets=plan.targets,
                inspected_fields=inspected_fields,
                secret_values=secret_values,
            )
            if rescue_destination is not None:
                final_exchange = call_and_log(
                    client,
                    run_log,
                    event="call_helicopter",
                    secret_values=secret_values,
                    call=lambda rescue_destination=rescue_destination: client.call_helicopter(
                        rescue_destination.label()
                    ),
                )
                break

    expenses_exchange = call_and_log(
        client,
        run_log,
        event="expenses",
        secret_values=secret_values,
        call=client.expenses,
    )
    used, left = parse_expense_totals(expenses_exchange.response.payload)

    status = "rescued" if final_exchange else "not_found"
    final_response_path: Path | None = None
    if final_exchange:
        final_response_path = (
            config.paths.output_dir / f"final_response_{run_log.run_id}.json"
        )
        write_json(final_response_path, exchange_to_dict(final_exchange))

    run_report_path = config.paths.output_dir / f"run_report_{run_log.run_id}.json"
    report = {
        "status": status,
        "run_id": run_log.run_id,
        "request_count": client.request_count(),
        "inspected_fields": inspected_fields,
        "rescue_destination": rescue_destination.label() if rescue_destination else None,
        "action_points_used": used,
        "action_points_left": left,
        "flag_found": contains_flag(final_exchange.response.payload if final_exchange else None),
        "final_response_path": str(final_response_path) if final_response_path else None,
    }
    write_json(run_report_path, report)

    return WorkflowResult(
        status=status,
        run_log_path=str(run_log.path),
        run_report_path=str(run_report_path),
        final_response_path=str(final_response_path) if final_response_path else None,
        inspected_fields=inspected_fields,
        rescue_destination=rescue_destination.label() if rescue_destination else None,
        action_points_used=used,
        action_points_left=left,
        flag_found=report["flag_found"],
    )
