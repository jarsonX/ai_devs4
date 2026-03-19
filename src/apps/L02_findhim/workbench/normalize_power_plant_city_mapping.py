from __future__ import annotations

from typing import Any

from ..api_client import normalize_city_name
from .common import load_workbench_artifact, save_workbench_artifact


def build_normalized_index(items: list[dict[str, Any]], city_key: str) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}

    for item in items:
        city = item[city_key]
        normalized_city = normalize_city_name(city)
        if normalized_city in index:
            raise ValueError(f"Duplicate normalized city key detected: {normalized_city}")

        index[normalized_city] = {
            **item,
            "normalized_city": normalized_city,
        }

    return index


def extract_power_plants() -> list[dict[str, Any]]:
    artifact = load_workbench_artifact("power_plants_response.json")
    power_plants = artifact["data"]["response_json"]["power_plants"]

    extracted: list[dict[str, Any]] = []
    for city, details in power_plants.items():
        extracted.append(
            {
                "city": city,
                "code": details["code"],
                "is_active": details["is_active"],
                "power": details["power"],
            }
        )

    return extracted


def extract_city_coordinates() -> list[dict[str, Any]]:
    artifact = load_workbench_artifact("power_plant_city_coordinates.json")
    return artifact["data"]["results"]


def main() -> None:
    power_plants = extract_power_plants()
    city_coordinates = extract_city_coordinates()

    power_plants_by_city = build_normalized_index(power_plants, "city")
    city_coordinates_by_city = build_normalized_index(city_coordinates, "city")

    missing_in_coordinates = sorted(
        normalized_city
        for normalized_city in power_plants_by_city
        if normalized_city not in city_coordinates_by_city
    )
    missing_in_power_plants = sorted(
        normalized_city
        for normalized_city in city_coordinates_by_city
        if normalized_city not in power_plants_by_city
    )

    if missing_in_coordinates or missing_in_power_plants:
        raise ValueError(
            "Normalized city mapping is incomplete. "
            f"Missing in coordinates: {missing_in_coordinates}. "
            f"Missing in power plants: {missing_in_power_plants}."
        )

    merged_cities: list[dict[str, Any]] = []
    for normalized_city in sorted(power_plants_by_city):
        power_plant = power_plants_by_city[normalized_city]
        coordinates = city_coordinates_by_city[normalized_city]
        merged_cities.append(
            {
                "normalized_city": normalized_city,
                "power_plant_city": power_plant["city"],
                "coordinate_city": coordinates["city"],
                "code": power_plant["code"],
                "is_active": power_plant["is_active"],
                "power": power_plant["power"],
                "latitude": coordinates["latitude"],
                "longitude": coordinates["longitude"],
            }
        )

    output_path = save_workbench_artifact(
        "normalized_power_plant_city_mapping.json",
        {
            "step": "normalize_power_plant_city_mapping",
            "cities_count": len(merged_cities),
            "missing_in_coordinates": missing_in_coordinates,
            "missing_in_power_plants": missing_in_power_plants,
            "results": merged_cities,
        },
    )

    print(f"Saved workbench artifact: {output_path}")


if __name__ == "__main__":
    main()
