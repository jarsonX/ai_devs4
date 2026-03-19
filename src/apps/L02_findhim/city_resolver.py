from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from .api_client import normalize_city_name
from .config import AppConfig
from .models import CityCoordinates


def build_city_coordinates_schema(cities: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "enum": cities,
                        },
                        "latitude": {
                            "type": "number",
                        },
                        "longitude": {
                            "type": "number",
                        },
                    },
                    "required": ["city", "latitude", "longitude"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["results"],
        "additionalProperties": False,
    }


def build_city_coordinates_prompt(cities: list[str]) -> str:
    return f"""
You provide representative geographic coordinates for Polish localities.

Task:
- For each city below, return one representative pair of coordinates in Poland.
- Use coordinates that represent the city itself, suitable for rough distance comparisons.
- Prefer the central, commonly recognized location of the locality.
- Return exactly one result for each input city.
- Preserve the original city names exactly as provided.

Cities:
{", ".join(cities)}

Return a JSON response that matches the schema exactly.
Do not add explanations or text outside the JSON.
""".strip()


def resolve_city_coordinates(config: AppConfig, cities: list[str]) -> list[CityCoordinates]:
    unique_cities = list(dict.fromkeys(city.strip() for city in cities if city.strip()))
    if not unique_cities:
        raise ValueError("At least one city is required to resolve coordinates.")

    client = OpenAI(api_key=config.openai_api_key)
    prompt = build_city_coordinates_prompt(unique_cities)
    schema = build_city_coordinates_schema(unique_cities)

    response = client.responses.create(
        model=config.openai_model,
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "power_plant_city_coordinates",
                "schema": schema,
                "strict": True,
            }
        },
    )

    data = json.loads(response.output_text)
    results = data.get("results")
    if not isinstance(results, list):
        raise ValueError("Missing results list in city coordinates response.")

    coordinates: list[CityCoordinates] = []
    for item in results:
        if not isinstance(item, dict):
            raise ValueError(f"Unsupported city coordinates entry: {item!r}")

        city = str(item["city"]).strip()
        coordinates.append(
            CityCoordinates(
                city=city,
                normalized_city=normalize_city_name(city),
                latitude=float(item["latitude"]),
                longitude=float(item["longitude"]),
            )
        )

    if len(coordinates) != len(unique_cities):
        raise ValueError("City coordinates response does not match the requested city count.")

    return coordinates
