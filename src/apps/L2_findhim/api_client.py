"""This file talks to the course APIs and turns raw HTTP responses into clean Python data."""

from __future__ import annotations

import json
from typing import Any
from unicodedata import combining, normalize

import requests

from .config import AppConfig
from .models import PersonLocation, PowerPlantRecord, VerificationAnswer


def normalize_city_name(city: str) -> str:
    normalized = normalize("NFKD", city)
    without_diacritics = "".join(
        character for character in normalized if not combining(character)
    )
    return " ".join(without_diacritics.lower().split())


def decode_json_response(response: requests.Response) -> Any:
    return json.loads(response.content.decode("utf-8"))


def extract_number(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid numeric value for {field_name}: {value!r}") from error


def parse_power_plants(payload: Any) -> list[PowerPlantRecord]:
    if not isinstance(payload, dict):
        raise ValueError("Power plants response must be a JSON object.")

    power_plants_payload = payload.get("power_plants")
    if not isinstance(power_plants_payload, dict):
        raise ValueError("Missing power_plants object in response.")

    power_plants: list[PowerPlantRecord] = []

    for city, details in power_plants_payload.items():
        if not isinstance(city, str) or not city.strip():
            raise ValueError(f"Invalid city name in power plants response: {city!r}")
        if not isinstance(details, dict):
            raise ValueError(f"Invalid power plant details for city {city!r}: {details!r}")

        code = details.get("code")
        is_active = details.get("is_active")
        power = details.get("power")

        if not isinstance(code, str) or not code.strip():
            raise ValueError(f"Missing power plant code for city {city!r}.")
        if not isinstance(is_active, bool):
            raise ValueError(f"Missing is_active flag for city {city!r}.")
        if not isinstance(power, str) or not power.strip():
            raise ValueError(f"Missing power description for city {city!r}.")

        power_plants.append(
            PowerPlantRecord(
                city=city.strip(),
                normalized_city=normalize_city_name(city),
                code=code.strip(),
                is_active=is_active,
                power=power.strip(),
            )
        )

    return power_plants


def parse_person_locations(payload: Any) -> list[PersonLocation]:
    if not isinstance(payload, list):
        raise ValueError("Location response must be a JSON list.")

    locations: list[PersonLocation] = []

    for item in payload:
        if not isinstance(item, dict):
            raise ValueError(f"Unsupported location entry: {item!r}")
        if "latitude" not in item or "longitude" not in item:
            raise ValueError(f"Missing coordinates in location entry: {item!r}")

        locations.append(
            PersonLocation(
                latitude=extract_number(item["latitude"], "latitude"),
                longitude=extract_number(item["longitude"], "longitude"),
            )
        )

    return locations


def parse_access_level(payload: Any) -> int:
    if not isinstance(payload, dict):
        raise ValueError("Access level response must be a JSON object.")

    value = payload.get("accessLevel")
    if value is None:
        raise ValueError(f"Missing accessLevel in payload: {payload!r}")

    return int(value)


class FindHimApiClient:
    def __init__(self, config: AppConfig, timeout: int = 30) -> None:
        self.config = config
        self.timeout = timeout
        self.session = requests.Session()

    def fetch_power_plants(self) -> list[PowerPlantRecord]:
        response = self.session.get(self.config.power_plants_url, timeout=self.timeout)
        response.raise_for_status()
        return parse_power_plants(decode_json_response(response))

    def get_person_locations(self, name: str, surname: str) -> list[PersonLocation]:
        payload = {
            "apikey": self.config.ai_devs_api_key,
            "name": name,
            "surname": surname,
        }
        response = self.session.post(
            self.config.location_api_url,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_person_locations(decode_json_response(response))

    def get_access_level(self, name: str, surname: str, birth_year: int) -> int:
        payload = {
            "apikey": self.config.ai_devs_api_key,
            "name": name,
            "surname": surname,
            "birthYear": birth_year,
        }
        response = self.session.post(
            self.config.access_level_api_url,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_access_level(decode_json_response(response))

    def verify_answer(self, answer: VerificationAnswer) -> dict[str, Any]:
        payload = {
            "apikey": self.config.ai_devs_api_key,
            "task": self.config.task_name,
            "answer": {
                "name": answer.name,
                "surname": answer.surname,
                "accessLevel": answer.accessLevel,
                "powerPlant": answer.powerPlant,
            },
        }
        response = self.session.post(
            self.config.verify_api_url,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return decode_json_response(response)
