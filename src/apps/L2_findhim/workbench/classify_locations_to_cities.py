from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from ..config import get_config
from .common import load_workbench_artifact, save_workbench_artifact


NONE_CITY = "NONE"


def build_location_classification_schema(allowed_cities: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer"},
                        "city": {
                            "type": "string",
                            "enum": [*allowed_cities, NONE_CITY],
                        },
                        "confidence": {
                            "type": "number",
                        },
                    },
                    "required": ["index", "city", "confidence"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["results"],
        "additionalProperties": False,
    }


def build_location_classification_prompt(
    allowed_cities: list[str],
    locations: list[dict[str, Any]],
) -> str:
    location_lines = [
        f'{index}. latitude={item["latitude"]}, longitude={item["longitude"]}'
        for index, item in enumerate(locations, start=1)
    ]
    locations_block = "\n".join(location_lines)

    return f"""
You classify geographic coordinates into one of the allowed Polish cities.

Allowed cities:
{", ".join(allowed_cities)}

Task:
- For each coordinate, choose exactly one city from the allowed list if the point is clearly in or very near that city.
- If the point does not clearly match any allowed city, return {NONE_CITY}.
- Base the decision on geographic knowledge of Poland.
- Treat this as a strict classification task, not an open-ended answer.
- Use higher confidence only when the match is clearly plausible.
- Prefer {NONE_CITY} over a weak guess.
- Preserve the input numbering.
- Return exactly one result per input item.

Input coordinates:
{locations_block}

Return a JSON response that matches the schema exactly.
Do not add explanations or text outside the JSON.
""".strip()


def extract_allowed_cities(power_plants_artifact: dict[str, Any]) -> list[str]:
    response_json = power_plants_artifact["data"]["response_json"]
    power_plants = response_json["power_plants"]
    return list(power_plants.keys())


def extract_locations(location_artifact: dict[str, Any]) -> list[dict[str, Any]]:
    response_json = location_artifact["data"]["response_json"]
    if not isinstance(response_json, list):
        raise ValueError("Expected location response_json to be a list.")

    return response_json


def main() -> None:
    config = get_config()
    client = OpenAI(api_key=config.openai_api_key)

    power_plants_artifact = load_workbench_artifact("power_plants_response.json")
    location_artifact = load_workbench_artifact("location_response.json")

    allowed_cities = extract_allowed_cities(power_plants_artifact)
    locations = extract_locations(location_artifact)
    prompt = build_location_classification_prompt(allowed_cities, locations)
    schema = build_location_classification_schema(allowed_cities)

    response = client.responses.create(
        model=config.openai_model,
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "location_city_classification",
                "schema": schema,
                "strict": True,
            }
        },
    )

    result = json.loads(response.output_text)
    output_path = save_workbench_artifact(
        "location_city_classification.json",
        {
            "step": "classify_locations_to_cities",
            "allowed_cities": allowed_cities,
            "suspect": location_artifact["data"]["suspect"],
            "results": result["results"],
        },
    )

    print(f"Saved workbench artifact: {output_path}")


if __name__ == "__main__":
    main()
