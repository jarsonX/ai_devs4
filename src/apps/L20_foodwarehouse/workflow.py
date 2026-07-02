# Deterministic planning and live execution for the L20 foodwarehouse task.

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.apps.L20_foodwarehouse.config import AppConfig, build_safe_config_summary
from src.apps.L20_foodwarehouse.models import (
    ApiResponse,
    CityDemand,
    LoggedExchange,
    OrderPlan,
    response_contains_flag,
)
from src.apps.L20_foodwarehouse.verify_client import FoodwarehouseVerifyClient


CITY_FIELD_HINTS = ("city", "miasto", "town", "name", "nazwa")
DESTINATION_FIELD_HINTS = (
    "destination",
    "destinationid",
    "destination_id",
    "destinationcode",
    "destination_code",
    "code",
    "kod",
    "target",
)
CREATOR_FIELD_HINTS = (
    "creatorid",
    "creator_id",
    "userid",
    "user_id",
    "workerid",
    "worker_id",
    "personid",
    "person_id",
    "employeeid",
    "employee_id",
)
ID_FIELD_HINTS = ("id", "userid", "user_id", "personid", "person_id", "creatorid")
SIGNATURE_RE = re.compile(r"\b[a-fA-F0-9]{40}\b")
SAFE_TABLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


# Write JSON with stable formatting for local learning artifacts.
def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# Convert a sequence of exchanges into runtime JSON data.
def exchanges_to_dict(exchanges: list[LoggedExchange]) -> list[dict[str, Any]]:
    return [exchange.to_dict() for exchange in exchanges]


# Normalize names so database matching is not blocked by case or accents.
def normalize_text(value: Any) -> str:
    text = str(value).strip().lower()
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


# Normalize field names for loose matching across unknown SQLite schemas.
def normalize_field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", normalize_text(value))


# Load and validate city demands from the local JSON file.
def load_city_demands(path: Path) -> list[CityDemand]:
    raw_data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, dict) or not raw_data:
        raise ValueError("food4cities.json must contain a non-empty object.")

    demands: list[CityDemand] = []
    for city, items in sorted(raw_data.items()):
        if not isinstance(city, str) or not city.strip():
            raise ValueError("Each city name must be a non-empty string.")
        if not isinstance(items, dict) or not items:
            raise ValueError(f"{city} must contain a non-empty item object.")

        normalized_items: dict[str, int] = {}
        for name, amount in sorted(items.items()):
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"{city} contains an invalid item name.")
            if not isinstance(amount, int) or amount <= 0:
                raise ValueError(f"{city}/{name} must be a positive integer.")
            normalized_items[name] = amount
        demands.append(CityDemand(city=city, items=normalized_items))
    return demands


# Convert SQLite-ish column/row structures into record dictionaries.
def records_from_column_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []

    columns = value.get("columns") or value.get("cols") or value.get("headers")
    rows = value.get("rows") or value.get("data")
    if not isinstance(columns, list) or not isinstance(rows, list):
        return []

    records: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            records.append(row)
        elif isinstance(row, list):
            records.append(dict(zip([str(column) for column in columns], row)))
    return records


# Walk an arbitrary API payload and collect record-like dictionaries.
def collect_records(value: Any) -> list[dict[str, Any]]:
    direct_records = records_from_column_rows(value)
    if direct_records:
        return direct_records

    if isinstance(value, list):
        if all(isinstance(item, dict) for item in value):
            return [dict(item) for item in value]
        records: list[dict[str, Any]] = []
        for item in value:
            records.extend(collect_records(item))
        return records

    if isinstance(value, dict):
        records: list[dict[str, Any]] = []
        for nested in value.values():
            records.extend(collect_records(nested))
        return records

    return []


# Walk an arbitrary API payload and collect visible string values.
def collect_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(collect_strings(item))
        return strings
    if isinstance(value, dict):
        strings = []
        for nested in value.values():
            strings.extend(collect_strings(nested))
        return strings
    return []


# Walk an arbitrary API payload and collect dictionaries for direct field lookup.
def collect_dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        dictionaries = [value]
        for nested in value.values():
            dictionaries.extend(collect_dicts(nested))
        return dictionaries
    if isinstance(value, list):
        dictionaries: list[dict[str, Any]] = []
        for nested in value:
            dictionaries.extend(collect_dicts(nested))
        return dictionaries
    return []


# Parse table names from the database tool response.
def extract_table_names(response: ApiResponse) -> list[str]:
    if isinstance(response.payload, dict) and isinstance(response.payload.get("tables"), list):
        return sorted(
            table
            for table in response.payload["tables"]
            if isinstance(table, str) and SAFE_TABLE_RE.match(table)
        )

    names: set[str] = set()
    for record in collect_records(response.payload):
        for key in ("name", "table", "table_name", "tbl_name"):
            value = get_field(record, (key,))
            if isinstance(value, str) and SAFE_TABLE_RE.match(value):
                names.add(value)

    for value in collect_strings(response.payload):
        candidate = value.strip()
        if SAFE_TABLE_RE.match(candidate) and candidate.lower() not in {
            "ok",
            "reply",
            "database",
            "read-only",
        }:
            names.add(candidate)

    return sorted(names)


# Read one field using normalized aliases.
def get_field(record: dict[str, Any], hints: Iterable[str]) -> Any | None:
    normalized_hints = {normalize_field_name(hint) for hint in hints}
    for key, value in record.items():
        if normalize_field_name(str(key)) in normalized_hints:
            return value
    return None


# Return whether a database record appears to describe one target city.
def record_matches_city(record: dict[str, Any], city: str) -> bool:
    normalized_city = normalize_text(city)
    for value in record.values():
        if isinstance(value, str) and normalize_text(value) == normalized_city:
            return True
    return False


# Convert one likely numeric identifier into int.
def parse_int_id(value: Any, *, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} cannot be a boolean.")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    raise ValueError(f"{label} must be an integer-compatible value, got {value!r}.")


# Keep destination values stable for the Hub request.
def parse_destination(value: Any) -> str:
    if value is None:
        raise ValueError("destination is missing.")
    destination = str(value).strip()
    if not destination:
        raise ValueError("destination is empty.")
    return destination


# Find the best database record for one city.
def find_city_record(city: str, records_by_table: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for records in records_by_table.values():
        for record in records:
            if record_matches_city(record, city):
                matches.append(record)

    if not matches:
        raise ValueError(f"No database record matched city {city}.")

    for record in matches:
        if get_field(record, DESTINATION_FIELD_HINTS) is not None:
            return record
    return matches[0]


# Escape a trusted local value before embedding it in a read-only SQL string.
def sql_string_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


# Fetch one city destination directly when the generic table scan was truncated.
def fetch_city_record(
    client: FoodwarehouseVerifyClient,
    exchanges: list[LoggedExchange],
    city: str,
    records_by_table: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    query = (
        "select * from destinations where lower(name) = lower("
        f"{sql_string_literal(city)}"
        ")"
    )
    exchange = client.database_query(query)
    exchanges.append(exchange)
    records = collect_records(exchange.response.payload)
    records_by_table.setdefault("destinations", []).extend(records)
    if not records:
        raise ValueError(f"No destination record found for city {city}.")
    return records[0]


# Find a city record locally first, then query the destination table directly.
def find_or_fetch_city_record(
    client: FoodwarehouseVerifyClient,
    exchanges: list[LoggedExchange],
    city: str,
    records_by_table: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    try:
        return find_city_record(city, records_by_table)
    except ValueError:
        return fetch_city_record(client, exchanges, city, records_by_table)


# Return whether a user record looks like an active transport handler.
def is_transport_creator(record: dict[str, Any]) -> bool:
    role = get_field(record, ("role", "role_id"))
    is_active = get_field(record, ("is_active", "active"))
    try:
        role_id = parse_int_id(role, label="role") if role is not None else 0
    except ValueError:
        role_id = 0
    if is_active in (0, "0", False):
        return False
    return role_id == 2


# Select one existing user that can create warehouse transport orders.
def choose_creator_record(records_by_table: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    user_records = records_by_table.get("users", [])
    for record in user_records:
        if is_transport_creator(record):
            return record
    for record in user_records:
        if get_field(record, ("login",)) is not None and get_field(record, ("birthday",)) is not None:
            return record
    raise ValueError("No usable creator user was found in the users table.")


# Find the creator id associated with the chosen user record.
def get_creator_id(creator_record: dict[str, Any]) -> int:
    creator_value = get_field(creator_record, ID_FIELD_HINTS)
    return parse_int_id(creator_value, label="creator id")


# Build plausible signature tool payloads from the discovered creator data.
def build_signature_payload_candidates(
    creator_id: int,
    creator_record: dict[str, Any],
    destination: str,
) -> list[dict[str, Any]]:
    login = get_field(creator_record, ("login",))
    birthday = get_field(creator_record, ("birthday",))
    candidates = [
        {
            "action": "generate",
            "login": login,
            "birthday": birthday,
            "destination": parse_int_id(destination, label="destination"),
        },
        {
            "action": "generate",
            "creatorID": creator_id,
            "destination": parse_int_id(destination, label="destination"),
        },
        {"creatorID": creator_id, "destination": destination},
        {"userID": creator_id, "destination": destination},
        {"id": creator_id, "destination": destination},
        {"user": creator_record, "destination": destination},
        {"data": creator_record, "destination": destination},
    ]

    flattened = {
        str(key): value
        for key, value in creator_record.items()
        if isinstance(value, (str, int, float, bool)) or value is None
    }
    if flattened:
        candidates.append(flattened)
    return candidates


# Extract a SHA1-looking signature from a signatureGenerator response.
def extract_signature(response: ApiResponse) -> str | None:
    strings = collect_strings(response.payload)
    strings.append(response.text)
    for value in strings:
        match = SIGNATURE_RE.search(value)
        if match:
            return match.group(0).lower()
    return None


# Call the signature generator with bounded compatible payload variants.
def generate_signature(
    client: FoodwarehouseVerifyClient,
    exchanges: list[LoggedExchange],
    *,
    creator_id: int,
    creator_record: dict[str, Any],
    destination: str,
) -> str:
    for candidate in build_signature_payload_candidates(creator_id, creator_record, destination):
        exchange = client.signature(candidate)
        exchanges.append(exchange)
        signature = extract_signature(exchange.response)
        if signature:
            return signature
    raise ValueError(
        "Could not obtain a SHA1 signature from signatureGenerator. "
        "Inspect the saved run report and adjust the payload mapping."
    )


# Extract an order id from an orders.create response.
def extract_order_id(response: ApiResponse) -> str:
    records = collect_records(response.payload)
    for record in records:
        value = get_field(record, ("id", "orderid", "order_id"))
        if value is not None:
            return str(value)

    for dictionary in collect_dicts(response.payload):
        value = get_field(dictionary, ("id", "orderid", "order_id"))
        if value is not None:
            return str(value)

    for value in collect_strings(response.payload):
        if value.strip() and normalize_text(value) not in {"ok", "created", "success"}:
            return value.strip()

    raise ValueError("orders.create did not return a detectable order id.")


# Query all discovered database tables through the read-only task API.
def fetch_database_records(
    client: FoodwarehouseVerifyClient,
    exchanges: list[LoggedExchange],
) -> dict[str, list[dict[str, Any]]]:
    tables_exchange = client.database_query("show tables")
    exchanges.append(tables_exchange)
    table_names = extract_table_names(tables_exchange.response)
    if not table_names:
        raise ValueError("The database tool did not return any table names.")

    records_by_table: dict[str, list[dict[str, Any]]] = {}
    for table_name in table_names:
        if not SAFE_TABLE_RE.match(table_name):
            continue
        query_exchange = client.database_query(f"select * from {table_name} limit 1000")
        exchanges.append(query_exchange)
        records_by_table[table_name] = collect_records(query_exchange.response.payload)

    if not any(records_by_table.values()):
        raise ValueError("No database rows were extracted from discovered tables.")
    return records_by_table


# Build all order plans from local demands plus discovered database records.
def build_order_plans(
    client: FoodwarehouseVerifyClient,
    exchanges: list[LoggedExchange],
    *,
    demands: list[CityDemand],
    records_by_table: dict[str, list[dict[str, Any]]],
) -> list[OrderPlan]:
    plans: list[OrderPlan] = []
    creator_record = choose_creator_record(records_by_table)
    creator_id = get_creator_id(creator_record)
    for demand in demands:
        city_record = find_or_fetch_city_record(
            client,
            exchanges,
            demand.city,
            records_by_table,
        )
        destination = parse_destination(get_field(city_record, DESTINATION_FIELD_HINTS))
        signature = generate_signature(
            client,
            exchanges,
            creator_id=creator_id,
            creator_record=creator_record,
            destination=destination,
        )
        plans.append(
            OrderPlan(
                city=demand.city,
                title=f"Delivery for {demand.city.title()}",
                creator_id=creator_id,
                destination=destination,
                signature=signature,
                items=demand.items,
            )
        )
    return plans


# Create and fill every remote order described by the plan.
def submit_order_plans(
    client: FoodwarehouseVerifyClient,
    exchanges: list[LoggedExchange],
    plans: list[OrderPlan],
) -> list[dict[str, Any]]:
    created: list[dict[str, Any]] = []
    for plan in plans:
        create_exchange = client.orders_create(
            title=plan.title,
            creator_id=plan.creator_id,
            destination=plan.destination,
            signature=plan.signature,
        )
        exchanges.append(create_exchange)
        order_id = extract_order_id(create_exchange.response)

        append_exchange = client.orders_append(order_id=order_id, items=plan.items)
        exchanges.append(append_exchange)
        created.append({"city": plan.city, "order_id": order_id})
    return created


# Return a secret-safe local summary of city demands.
def build_dry_run_summary(config: AppConfig, demands: list[CityDemand]) -> dict[str, Any]:
    return {
        "mode": "dry-run",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config": build_safe_config_summary(config),
        "city_count": len(demands),
        "demands": [asdict(demand) for demand in demands],
    }


# Run the local validation path and write a planned-demand artifact.
def run_dry_run(config: AppConfig) -> dict[str, Any]:
    demands = load_city_demands(config.paths.input_file)
    summary = build_dry_run_summary(config, demands)
    output_path = config.paths.output_dir / "planned_demands.json"
    write_json(output_path, summary)
    return {
        "status": "dry_run_ok",
        "city_count": len(demands),
        "planned_demands_path": str(output_path.relative_to(config.paths.repo_root)),
    }


# Run a read-only remote inspection to capture the real task API shape.
def run_inspect_remote(config: AppConfig) -> dict[str, Any]:
    if config.hub is None:
        raise ValueError("Hub config is required for remote inspection mode.")

    exchanges: list[LoggedExchange] = []
    client = FoodwarehouseVerifyClient(
        config.hub,
        timeout_seconds=config.runtime.request_timeout_seconds,
        max_requests=config.runtime.max_verify_requests,
    )
    exchanges.append(client.help())
    records_by_table = fetch_database_records(client, exchanges)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    inspection_path = config.paths.output_dir / f"remote_inspection_{stamp}.json"
    write_json(
        inspection_path,
        {
            "mode": "inspect-remote",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "config": build_safe_config_summary(config),
            "request_count": client.request_count(),
            "tables": {
                table_name: {
                    "row_count": len(records),
                    "sample_rows": records[:5],
                }
                for table_name, records in records_by_table.items()
            },
            "exchanges": exchanges_to_dict(exchanges),
        },
    )
    return {
        "status": "inspection_ok",
        "request_count": client.request_count(),
        "table_names": sorted(records_by_table),
        "inspection_path": str(inspection_path.relative_to(config.paths.repo_root)),
    }


# Run the live Hub submission path and preserve raw API feedback in runtime data.
def run_submit(config: AppConfig) -> dict[str, Any]:
    if config.hub is None:
        raise ValueError("Hub config is required for submit mode.")

    exchanges: list[LoggedExchange] = []
    demands = load_city_demands(config.paths.input_file)
    client = FoodwarehouseVerifyClient(
        config.hub,
        timeout_seconds=config.runtime.request_timeout_seconds,
        max_requests=config.runtime.max_verify_requests,
    )

    exchanges.append(client.help())
    exchanges.append(client.reset())
    records_by_table = fetch_database_records(client, exchanges)
    plans = build_order_plans(
        client,
        exchanges,
        demands=demands,
        records_by_table=records_by_table,
    )
    created_orders = submit_order_plans(client, exchanges, plans)
    exchanges.append(client.orders_get())
    exchanges.append(client.done())
    final_response = exchanges[-1].response

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_report_path = config.paths.output_dir / f"run_report_{stamp}.json"
    final_response_path = config.paths.output_dir / f"final_response_{stamp}.json"

    write_json(
        run_report_path,
        {
            "mode": "submit",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "config": build_safe_config_summary(config),
            "city_count": len(demands),
            "request_count": client.request_count(),
            "created_orders": created_orders,
            "planned_orders": [asdict(plan) for plan in plans],
            "flag_found": response_contains_flag(final_response),
            "exchanges": exchanges_to_dict(exchanges),
        },
    )
    write_json(
        final_response_path,
        {
            "status_code": final_response.status_code,
            "payload": final_response.payload,
            "text": final_response.text,
            "flag_found": response_contains_flag(final_response),
        },
    )

    return {
        "status": "solved" if response_contains_flag(final_response) else "submitted",
        "city_count": len(demands),
        "request_count": client.request_count(),
        "run_report_path": str(run_report_path.relative_to(config.paths.repo_root)),
        "final_response_path": str(final_response_path.relative_to(config.paths.repo_root)),
        "flag_found": response_contains_flag(final_response),
        "final_payload": final_response.payload,
        "final_text": final_response.text,
    }
