from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from ..config import get_config
from .classify_locations_to_cities import extract_allowed_cities
from .common import load_workbench_artifact, save_workbench_artifact


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


def main() -> None:
    config = get_config()
    client = OpenAI(api_key=config.openai_api_key)

    power_plants_artifact = load_workbench_artifact("power_plants_response.json")
    cities = extract_allowed_cities(power_plants_artifact)
    prompt = build_city_coordinates_prompt(cities)
    schema = build_city_coordinates_schema(cities)

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

    result = json.loads(response.output_text)
    output_path = save_workbench_artifact(
        "power_plant_city_coordinates.json",
        {
            "step": "resolve_power_plant_city_coordinates",
            "cities": cities,
            "results": result["results"],
        },
    )

    print(f"Saved workbench artifact: {output_path}")


if __name__ == "__main__":
    main()
