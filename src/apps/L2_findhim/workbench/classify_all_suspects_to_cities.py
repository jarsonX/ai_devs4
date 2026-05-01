from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from ..models import Suspect
from .classify_locations_to_cities import (
    NONE_CITY,
    build_location_classification_prompt,
    build_location_classification_schema,
    extract_allowed_cities,
)
from .common import (
    get_all_suspects,
    get_config_with_session,
    load_workbench_artifact,
    save_workbench_artifact,
)


def fetch_locations_for_suspect(
    location_api_url: str,
    api_key: str,
    suspect: Suspect,
    timeout: int,
    session: Any,
) -> list[dict[str, Any]]:
    payload = {
        "apikey": api_key,
        "name": suspect.name,
        "surname": suspect.surname,
    }
    response = session.post(
        location_api_url,
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    response_json = response.json()

    if not isinstance(response_json, list):
        raise ValueError(
            f"Expected a list of locations for {suspect.name} {suspect.surname}."
        )

    return response_json


def classify_locations(
    client: OpenAI,
    model: str,
    allowed_cities: list[str],
    locations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    prompt = build_location_classification_prompt(allowed_cities, locations)
    schema = build_location_classification_schema(allowed_cities)

    response = client.responses.create(
        model=model,
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
    return result["results"]


def summarize_classification_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    city_summary: dict[str, dict[str, Any]] = {}

    for item in results:
        city = item["city"]
        if city == NONE_CITY:
            continue

        summary = city_summary.setdefault(
            city,
            {
                "city": city,
                "match_count": 0,
                "max_confidence": 0.0,
                "avg_confidence": 0.0,
                "confidence_sum": 0.0,
            },
        )
        confidence = float(item["confidence"])
        summary["match_count"] += 1
        summary["confidence_sum"] += confidence
        summary["max_confidence"] = max(summary["max_confidence"], confidence)

    summarized = list(city_summary.values())
    for item in summarized:
        item["avg_confidence"] = round(item["confidence_sum"] / item["match_count"], 4)
        del item["confidence_sum"]

    summarized.sort(
        key=lambda item: (
            -item["match_count"],
            -item["max_confidence"],
            -item["avg_confidence"],
            item["city"],
        )
    )
    return summarized


def build_enriched_results(
    locations: list[dict[str, Any]],
    classifications: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    enriched_results: list[dict[str, Any]] = []

    for location, classification in zip(locations, classifications, strict=True):
        enriched_results.append(
            {
                "index": classification["index"],
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "city": classification["city"],
                "confidence": classification["confidence"],
            }
        )

    return enriched_results


def main() -> None:
    config, session, timeout = get_config_with_session()
    client = OpenAI(api_key=config.openai_api_key)

    power_plants_artifact = load_workbench_artifact("power_plants_response.json")
    allowed_cities = extract_allowed_cities(power_plants_artifact)
    suspects = get_all_suspects(config)

    classified_suspects: list[dict[str, Any]] = []

    for suspect in suspects:
        locations = fetch_locations_for_suspect(
            location_api_url=config.location_api_url,
            api_key=config.ai_devs_api_key,
            suspect=suspect,
            timeout=timeout,
            session=session,
        )
        classifications = classify_locations(
            client=client,
            model=config.openai_model,
            allowed_cities=allowed_cities,
            locations=locations,
        )
        enriched_results = build_enriched_results(locations, classifications)
        summary = summarize_classification_results(enriched_results)

        classified_suspects.append(
            {
                "suspect": {
                    "name": suspect.name,
                    "surname": suspect.surname,
                    "birthYear": suspect.birth_year,
                },
                "locations_count": len(locations),
                "classified_locations": enriched_results,
                "city_summary": summary,
            }
        )

    output_path = save_workbench_artifact(
        "all_suspects_city_classification.json",
        {
            "step": "classify_all_suspects_to_cities",
            "allowed_cities": allowed_cities,
            "suspects": classified_suspects,
        },
    )

    print(f"Saved workbench artifact: {output_path}")


if __name__ == "__main__":
    main()
