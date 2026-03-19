from __future__ import annotations

from typing import Any

from ..geo import haversine_km
from ..models import Suspect
from .classify_all_suspects_to_cities import fetch_locations_for_suspect
from .common import (
    get_all_suspects,
    get_config_with_session,
    load_workbench_artifact,
    save_workbench_artifact,
)


def load_power_plant_city_mapping() -> list[dict[str, Any]]:
    artifact = load_workbench_artifact("normalized_power_plant_city_mapping.json")
    results = artifact["data"]["results"]
    if not isinstance(results, list):
        raise ValueError("Expected normalized power plant city mapping results to be a list.")

    return results


def find_best_distance_for_suspect(
    suspect: Suspect,
    locations: list[dict[str, Any]],
    power_plant_cities: list[dict[str, Any]],
) -> dict[str, Any]:
    best_match: dict[str, Any] | None = None

    for index, location in enumerate(locations, start=1):
        latitude = float(location["latitude"])
        longitude = float(location["longitude"])

        for city in power_plant_cities:
            distance_km = haversine_km(
                latitude,
                longitude,
                float(city["latitude"]),
                float(city["longitude"]),
            )

            if best_match is None or distance_km < best_match["distance_km"]:
                best_match = {
                    "suspect": {
                        "name": suspect.name,
                        "surname": suspect.surname,
                        "birthYear": suspect.birth_year,
                    },
                    "power_plant_city": city["power_plant_city"],
                    "normalized_city": city["normalized_city"],
                    "power_plant_code": city["code"],
                    "is_active": city["is_active"],
                    "power": city["power"],
                    "distance_km": round(distance_km, 4),
                    "location_index": index,
                    "location_latitude": latitude,
                    "location_longitude": longitude,
                    "city_latitude": city["latitude"],
                    "city_longitude": city["longitude"],
                }

    if best_match is None:
        raise ValueError(f"No locations found for suspect {suspect.name} {suspect.surname}.")

    return best_match


def build_global_ranking(suspect_best_matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        suspect_best_matches,
        key=lambda item: (
            item["distance_km"],
            item["suspect"]["surname"],
            item["suspect"]["name"],
        ),
    )


def main() -> None:
    config, session, timeout = get_config_with_session()
    suspects = get_all_suspects(config)
    power_plant_cities = load_power_plant_city_mapping()

    suspect_best_matches: list[dict[str, Any]] = []

    for suspect in suspects:
        locations = fetch_locations_for_suspect(
            location_api_url=config.location_api_url,
            api_key=config.ai_devs_api_key,
            suspect=suspect,
            timeout=timeout,
            session=session,
        )
        best_match = find_best_distance_for_suspect(
            suspect=suspect,
            locations=locations,
            power_plant_cities=power_plant_cities,
        )
        best_match["locations_count"] = len(locations)
        suspect_best_matches.append(best_match)

    ranking = build_global_ranking(suspect_best_matches)

    output_path = save_workbench_artifact(
        "candidate_distance_ranking.json",
        {
            "step": "calculate_candidate_distances",
            "suspect_best_matches": suspect_best_matches,
            "global_ranking": ranking,
            "best_candidate": ranking[0] if ranking else None,
        },
    )

    print(f"Saved workbench artifact: {output_path}")


if __name__ == "__main__":
    main()
