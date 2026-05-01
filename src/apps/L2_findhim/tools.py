"""This file defines the tools the agent can use and contains the Python logic behind each tool."""

from __future__ import annotations

import re
from typing import Any

from .api_client import FindHimApiClient
from .city_resolver import resolve_city_coordinates
from .config import AppConfig
from .data_loader import load_suspects
from .distance import find_best_distance_for_suspect
from .models import PowerPlantCity, Suspect, VerificationAnswer


TOOL_STAGE_GROUPS = {
    "setup": [
        "get_suspects",
        "get_power_plants",
        "resolve_power_plant_city_coordinates",
        "combine_power_plants_with_coordinates",
    ],
    "ranking": [
        "rank_suspects_by_distance",
    ],
    "finalize": [
        "get_access_level",
        "build_verification_answer",
    ],
}


def serialize_suspects(suspects: list) -> list[dict[str, Any]]:
    return [
        {
            "name": suspect.name,
            "surname": suspect.surname,
            "birthYear": suspect.birth_year,
        }
        for suspect in suspects
    ]


def serialize_power_plants(power_plants: list) -> list[dict[str, Any]]:
    return [
        {
            "city": power_plant.city,
            "normalizedCity": power_plant.normalized_city,
            "code": power_plant.code,
            "isActive": power_plant.is_active,
            "power": power_plant.power,
        }
        for power_plant in power_plants
    ]


def serialize_city_coordinates(coordinates: list) -> list[dict[str, Any]]:
    return [
        {
            "city": item.city,
            "normalizedCity": item.normalized_city,
            "latitude": item.latitude,
            "longitude": item.longitude,
        }
        for item in coordinates
    ]


def serialize_power_plant_cities(power_plant_cities: list[PowerPlantCity]) -> list[dict[str, Any]]:
    return [
        {
            "city": item.city,
            "normalizedCity": item.normalized_city,
            "code": item.code,
            "latitude": item.latitude,
            "longitude": item.longitude,
        }
        for item in power_plant_cities
    ]


def serialize_candidate_distance(candidate_distance) -> dict[str, Any]:
    return {
        "suspect": {
            "name": candidate_distance.suspect.name,
            "surname": candidate_distance.suspect.surname,
            "birthYear": candidate_distance.suspect.birth_year,
        },
        "powerPlantCode": candidate_distance.power_plant_code,
        "powerPlantCity": candidate_distance.power_plant_city,
        "distanceKm": round(candidate_distance.distance_km, 4),
        "observedLatitude": candidate_distance.observed_latitude,
        "observedLongitude": candidate_distance.observed_longitude,
    }


def sort_candidate_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        matches,
        key=lambda item: (
            float(item["distanceKm"]),
            str(item["suspect"]["surname"]),
            str(item["suspect"]["name"]),
        ),
    )


def build_tool_definitions(allowed_names: list[str] | None = None) -> list[dict]:
    tool_definitions = [
        {
            "type": "function",
            "name": "get_suspects",
            "description": "Load the list of suspects from the result of task L1.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "get_power_plants",
            "description": "Fetch the list of power plant records with city names and plant codes.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "resolve_power_plant_city_coordinates",
            "description": (
                "Resolve representative coordinates for the given Polish cities. "
                "Use this only for the closed list of power plant cities."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cities": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                        "minItems": 1,
                    }
                },
                "required": ["cities"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "combine_power_plants_with_coordinates",
            "description": (
                "Combine power plant records with resolved city coordinates by normalized city name."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "powerPlants": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "city": {"type": "string"},
                                "normalizedCity": {"type": "string"},
                                "code": {"type": "string"},
                                "isActive": {"type": "boolean"},
                                "power": {"type": "string"},
                            },
                            "required": ["city", "normalizedCity", "code", "isActive", "power"],
                            "additionalProperties": False,
                        },
                    },
                    "cityCoordinates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "city": {"type": "string"},
                                "normalizedCity": {"type": "string"},
                                "latitude": {"type": "number"},
                                "longitude": {"type": "number"},
                            },
                            "required": ["city", "normalizedCity", "latitude", "longitude"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["powerPlants", "cityCoordinates"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "get_access_level",
            "description": "Fetch the access level for one suspect.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "surname": {"type": "string"},
                    "birthYear": {"type": "integer"},
                },
                "required": ["name", "surname", "birthYear"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "rank_suspects_by_distance",
            "description": (
                "For all suspects, fetch their locations, compute the shortest distance to the "
                "power plant cities, and return a ranking from the shortest distance to the longest."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "suspects": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "surname": {"type": "string"},
                                "birthYear": {"type": "integer"},
                            },
                            "required": ["name", "surname", "birthYear"],
                            "additionalProperties": False,
                        },
                    },
                    "powerPlantCities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "city": {"type": "string"},
                                "normalizedCity": {"type": "string"},
                                "code": {"type": "string"},
                                "latitude": {"type": "number"},
                                "longitude": {"type": "number"},
                            },
                            "required": ["city", "normalizedCity", "code", "latitude", "longitude"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["suspects", "powerPlantCities"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "build_verification_answer",
            "description": (
                "Build the final answer object for the /verify request. "
                "The powerPlant field must contain only the exact plant code, for example PWR1234PL."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "surname": {"type": "string"},
                    "accessLevel": {"type": "integer"},
                    "powerPlant": {
                        "type": "string",
                        "pattern": "^PWR\\d{4}PL$",
                    },
                },
                "required": ["name", "surname", "accessLevel", "powerPlant"],
                "additionalProperties": False,
            },
        },
    ]

    if allowed_names is None:
        return tool_definitions

    allowed_name_set = set(allowed_names)
    return [
        tool_definition
        for tool_definition in tool_definitions
        if tool_definition["name"] in allowed_name_set
    ]


class FindHimToolbox:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.api_client = FindHimApiClient(config)

    def get_suspects(self) -> dict[str, Any]:
        suspects = load_suspects(self.config.suspects_source_path)
        return {
            "suspects": serialize_suspects(suspects),
        }

    def get_power_plants(self) -> dict[str, Any]:
        power_plants = self.api_client.fetch_power_plants()
        return {
            "powerPlants": serialize_power_plants(power_plants),
        }

    def resolve_power_plant_city_coordinates(self, cities: list[str]) -> dict[str, Any]:
        coordinates = resolve_city_coordinates(self.config, cities)
        return {
            "cityCoordinates": serialize_city_coordinates(coordinates),
        }

    def combine_power_plants_with_coordinates(
        self,
        power_plants: list[dict[str, Any]],
        city_coordinates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        power_plants_by_city = {
            str(item["normalizedCity"]).strip(): item
            for item in power_plants
        }
        city_coordinates_by_city = {
            str(item["normalizedCity"]).strip(): item
            for item in city_coordinates
        }

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

        combined: list[PowerPlantCity] = []
        for normalized_city in sorted(power_plants_by_city):
            power_plant = power_plants_by_city[normalized_city]
            coordinates = city_coordinates_by_city[normalized_city]
            combined.append(
                PowerPlantCity(
                    city=str(power_plant["city"]).strip(),
                    normalized_city=normalized_city,
                    code=str(power_plant["code"]).strip(),
                    latitude=float(coordinates["latitude"]),
                    longitude=float(coordinates["longitude"]),
                )
            )

        return {
            "powerPlantCities": serialize_power_plant_cities(combined),
        }

    def get_access_level(self, name: str, surname: str, birth_year: int) -> dict[str, Any]:
        access_level = self.api_client.get_access_level(name, surname, birth_year)
        return {
            "accessLevel": access_level,
        }

    def rank_suspects_by_distance(
        self,
        suspects_data: list[dict[str, Any]],
        power_plant_cities_data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        suspects = [
            Suspect(
                name=str(item["name"]).strip(),
                surname=str(item["surname"]).strip(),
                birth_year=int(item["birthYear"]),
            )
            for item in suspects_data
        ]
        power_plant_cities = [
            PowerPlantCity(
                city=str(item["city"]).strip(),
                normalized_city=str(item["normalizedCity"]).strip(),
                code=str(item["code"]).strip(),
                latitude=float(item["latitude"]),
                longitude=float(item["longitude"]),
            )
            for item in power_plant_cities_data
        ]

        matches: list[dict[str, Any]] = []
        for suspect in suspects:
            locations = self.api_client.get_person_locations(suspect.name, suspect.surname)
            candidate_distance = find_best_distance_for_suspect(
                suspect=suspect,
                locations=locations,
                power_plant_cities=power_plant_cities,
            )
            match = serialize_candidate_distance(candidate_distance)
            match["locationsCount"] = len(locations)
            matches.append(match)

        ranking = sort_candidate_matches(matches)
        return {
            "ranking": ranking,
            "bestCandidate": ranking[0] if ranking else None,
        }

    def build_verification_answer(
        self,
        name: str,
        surname: str,
        access_level: int,
        power_plant: str,
    ) -> dict[str, Any]:
        if not re.fullmatch(r"PWR\d{4}PL", power_plant.strip()):
            raise ValueError(
                "powerPlant must contain only the exact plant code in the format PWR1234PL."
            )

        answer = VerificationAnswer(
            name=name,
            surname=surname,
            accessLevel=access_level,
            powerPlant=power_plant.strip(),
        )
        return {
            "answer": {
                "name": answer.name,
                "surname": answer.surname,
                "accessLevel": answer.accessLevel,
                "powerPlant": answer.powerPlant,
            }
        }

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "get_suspects":
            return self.get_suspects()

        if tool_name == "get_power_plants":
            return self.get_power_plants()

        if tool_name == "resolve_power_plant_city_coordinates":
            cities = arguments.get("cities")
            if not isinstance(cities, list) or not all(isinstance(city, str) for city in cities):
                raise ValueError("Tool resolve_power_plant_city_coordinates requires a string array 'cities'.")

            return self.resolve_power_plant_city_coordinates(cities)

        if tool_name == "combine_power_plants_with_coordinates":
            power_plants = arguments.get("powerPlants")
            city_coordinates = arguments.get("cityCoordinates")
            if not isinstance(power_plants, list) or not isinstance(city_coordinates, list):
                raise ValueError(
                    "Tool combine_power_plants_with_coordinates requires list fields "
                    "'powerPlants' and 'cityCoordinates'."
                )

            return self.combine_power_plants_with_coordinates(power_plants, city_coordinates)

        if tool_name == "get_access_level":
            name = arguments.get("name")
            surname = arguments.get("surname")
            birth_year = arguments.get("birthYear")
            if not isinstance(name, str) or not isinstance(surname, str) or not isinstance(
                birth_year, int
            ):
                raise ValueError(
                    "Tool get_access_level requires 'name', 'surname', and integer 'birthYear'."
                )

            return self.get_access_level(name, surname, birth_year)

        if tool_name == "rank_suspects_by_distance":
            suspects = arguments.get("suspects")
            power_plant_cities = arguments.get("powerPlantCities")
            if not isinstance(suspects, list) or not isinstance(power_plant_cities, list):
                raise ValueError(
                    "Tool rank_suspects_by_distance requires 'suspects' and "
                    "'powerPlantCities' list arguments."
                )

            return self.rank_suspects_by_distance(suspects, power_plant_cities)

        if tool_name == "build_verification_answer":
            name = arguments.get("name")
            surname = arguments.get("surname")
            access_level = arguments.get("accessLevel")
            power_plant = arguments.get("powerPlant")
            if not isinstance(name, str) or not isinstance(surname, str) or not isinstance(
                access_level, int
            ) or not isinstance(power_plant, str):
                raise ValueError(
                    "Tool build_verification_answer requires 'name', 'surname', integer "
                    "'accessLevel', and 'powerPlant'."
                )

            return self.build_verification_answer(name, surname, access_level, power_plant)

        raise ValueError(f"Unsupported tool: {tool_name}")
