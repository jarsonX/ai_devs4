from __future__ import annotations

import re
from typing import Any

from .api_client import FindHimApiClient
from .config import AppConfig


def validate_agent_result(config: AppConfig, agent_status: dict[str, Any]) -> dict[str, Any]:
    if agent_status.get("status") != "completed":
        raise ValueError("Agent did not finish with status='completed'.")

    answer = agent_status.get("answer")
    if not isinstance(answer, dict):
        raise ValueError("Agent result is missing the final answer object.")

    best_candidate = agent_status.get("bestCandidate")
    if not isinstance(best_candidate, dict):
        raise ValueError("Agent result is missing the bestCandidate object.")

    name = answer.get("name")
    surname = answer.get("surname")
    access_level = answer.get("accessLevel")
    power_plant = answer.get("powerPlant")

    if not isinstance(name, str) or not name.strip():
        raise ValueError("Answer.name must be a non-empty string.")
    if not isinstance(surname, str) or not surname.strip():
        raise ValueError("Answer.surname must be a non-empty string.")
    if not isinstance(access_level, int):
        raise ValueError("Answer.accessLevel must be an integer.")
    if not isinstance(power_plant, str) or not re.fullmatch(r"PWR\d{4}PL", power_plant.strip()):
        raise ValueError("Answer.powerPlant must match the format PWR1234PL.")

    best_name = best_candidate.get("name")
    best_surname = best_candidate.get("surname")
    best_code = best_candidate.get("powerPlantCode")
    best_distance = best_candidate.get("distanceKm")

    if name != best_name or surname != best_surname:
        raise ValueError("Final answer does not match the best candidate selected by the agent.")
    if power_plant != best_code:
        raise ValueError("Final answer powerPlant does not match bestCandidate.powerPlantCode.")
    if not isinstance(best_distance, (int, float)) or float(best_distance) < 0:
        raise ValueError("bestCandidate.distanceKm must be a non-negative number.")

    api_client = FindHimApiClient(config)
    valid_codes = {item.code for item in api_client.fetch_power_plants()}
    if power_plant not in valid_codes:
        raise ValueError("Final answer powerPlant is not present in the power plants API response.")

    return {
        "isValid": True,
        "validatedAnswer": {
            "name": name,
            "surname": surname,
            "accessLevel": access_level,
            "powerPlant": power_plant,
        },
        "bestCandidate": {
            "name": best_name,
            "surname": best_surname,
            "powerPlantCode": best_code,
            "distanceKm": float(best_distance),
        },
        "checks": [
            "agent status is completed",
            "answer has required fields and types",
            "powerPlant matches expected code format",
            "answer matches bestCandidate",
            "powerPlant exists in live power plants API response",
        ],
    }
