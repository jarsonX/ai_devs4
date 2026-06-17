# This module loads and validates the local negotiations catalog CSV files.

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypeVar

from .config import AppConfig

T = TypeVar("T")

# Represent one city row from cities.csv.
@dataclass(frozen=True)
class City:
    name: str
    code: str


# Represent one item row from items.csv.
@dataclass(frozen=True)
class Item:
    name: str
    code: str


# Represent one item-to-city availability relation.
@dataclass(frozen=True)
class Connection:
    item_code: str
    city_code: str


# Keep the validated catalog plus lookup maps used by later batches.
@dataclass(frozen=True)
class Catalog:
    cities: tuple[City, ...]
    items: tuple[Item, ...]
    connections: tuple[Connection, ...]
    city_by_code: dict[str, City]
    item_by_code: dict[str, Item]
    city_codes_by_item_code: dict[str, frozenset[str]]

    # Count catalog items that exist but have no city availability.
    def unavailable_item_count(self) -> int:
        return len(set(self.item_by_code) - set(self.city_codes_by_item_code))

    # Build a compact summary for local startup and data verification.
    def summary(self) -> dict[str, int]:
        return {
            "cities": len(self.cities),
            "items": len(self.items),
            "connections": len(self.connections),
            "available_items": len(self.city_codes_by_item_code),
            "unavailable_items": self.unavailable_item_count(),
        }


# Raise one clear exception type for catalog integrity failures.
class CatalogValidationError(ValueError):
    pass


# Read one CSV file as dictionaries and validate its required columns.
def read_csv_rows(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    if not path.exists():
        raise CatalogValidationError(f"Missing catalog file: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = set(reader.fieldnames or [])
        missing_columns = required_columns - fieldnames
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise CatalogValidationError(f"{path.name} is missing columns: {missing}")

        rows: list[dict[str, str]] = []
        for row_number, raw_row in enumerate(reader, start=2):
            cleaned_row = {
                column: (raw_row.get(column) or "").strip()
                for column in required_columns
            }
            empty_columns = [
                column for column, value in cleaned_row.items() if not value
            ]
            if empty_columns:
                columns = ", ".join(sorted(empty_columns))
                raise CatalogValidationError(
                    f"{path.name}:{row_number} has empty columns: {columns}"
                )
            rows.append(cleaned_row)

    return rows


# Build a code lookup and reject duplicate stable identifiers.
def build_unique_lookup(
    records: tuple[T, ...],
    code_getter: Callable[[T], str],
    record_label: str,
) -> dict[str, T]:
    lookup: dict[str, T] = {}
    for record in records:
        code = code_getter(record)
        if code in lookup:
            raise CatalogValidationError(f"Duplicate {record_label} code: {code}")
        lookup[code] = record
    return lookup


# Load cities.csv into validated City records.
def load_cities(path: Path) -> tuple[City, ...]:
    rows = read_csv_rows(path, {"name", "code"})
    return tuple(City(name=row["name"], code=row["code"]) for row in rows)


# Load items.csv into validated Item records.
def load_items(path: Path) -> tuple[Item, ...]:
    rows = read_csv_rows(path, {"name", "code"})
    return tuple(Item(name=row["name"], code=row["code"]) for row in rows)


# Load connections.csv into validated Connection records.
def load_connections(path: Path) -> tuple[Connection, ...]:
    rows = read_csv_rows(path, {"itemCode", "cityCode"})
    return tuple(
        Connection(item_code=row["itemCode"], city_code=row["cityCode"])
        for row in rows
    )


# Validate cross-file references and precompute item availability.
def build_availability_map(
    connections: tuple[Connection, ...],
    item_by_code: dict[str, Item],
    city_by_code: dict[str, City],
) -> dict[str, frozenset[str]]:
    mutable_map: dict[str, set[str]] = {}
    for index, connection in enumerate(connections, start=1):
        if connection.item_code not in item_by_code:
            raise CatalogValidationError(
                f"connections.csv row {index} references unknown item code: "
                f"{connection.item_code}"
            )
        if connection.city_code not in city_by_code:
            raise CatalogValidationError(
                f"connections.csv row {index} references unknown city code: "
                f"{connection.city_code}"
            )
        mutable_map.setdefault(connection.item_code, set()).add(connection.city_code)

    return {
        item_code: frozenset(city_codes)
        for item_code, city_codes in mutable_map.items()
    }


# Load the full catalog from configured input CSV files.
def load_catalog(config: AppConfig) -> Catalog:
    cities = load_cities(config.paths.cities_csv)
    items = load_items(config.paths.items_csv)
    connections = load_connections(config.paths.connections_csv)
    city_by_code = build_unique_lookup(cities, lambda city: city.code, "city")
    item_by_code = build_unique_lookup(items, lambda item: item.code, "item")
    city_codes_by_item_code = build_availability_map(
        connections,
        item_by_code,
        city_by_code,
    )

    return Catalog(
        cities=cities,
        items=items,
        connections=connections,
        city_by_code=city_by_code,
        item_by_code=item_by_code,
        city_codes_by_item_code=city_codes_by_item_code,
    )
