"""This file calculates geographic distances and finds which power plant is closest to a suspect."""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from .models import CandidateDistance, PersonLocation, PowerPlantCity, Suspect


def haversine_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    earth_radius_km = 6371.0

    lat_a = radians(latitude_a)
    lon_a = radians(longitude_a)
    lat_b = radians(latitude_b)
    lon_b = radians(longitude_b)

    delta_lat = lat_b - lat_a
    delta_lon = lon_b - lon_a

    haversine = (
        sin(delta_lat / 2) ** 2
        + cos(lat_a) * cos(lat_b) * sin(delta_lon / 2) ** 2
    )
    arc = 2 * asin(sqrt(haversine))
    return earth_radius_km * arc


def find_best_distance_for_suspect(
    suspect: Suspect,
    locations: list[PersonLocation],
    power_plant_cities: list[PowerPlantCity],
) -> CandidateDistance:
    best_match: CandidateDistance | None = None

    for location in locations:
        for power_plant_city in power_plant_cities:
            distance_km = haversine_km(
                location.latitude,
                location.longitude,
                power_plant_city.latitude,
                power_plant_city.longitude,
            )

            if best_match is None or distance_km < best_match.distance_km:
                best_match = CandidateDistance(
                    suspect=suspect,
                    power_plant_code=power_plant_city.code,
                    power_plant_city=power_plant_city.city,
                    distance_km=distance_km,
                    observed_latitude=location.latitude,
                    observed_longitude=location.longitude,
                )

    if best_match is None:
        raise ValueError(f"No locations available for suspect {suspect.name} {suspect.surname}.")

    return best_match
