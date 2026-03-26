from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Person


def load_people_data(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError("People data file must contain a JSON object.")
    
    return payload


def require_non_empty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string.")
    
    cleaned_value = value.strip()
    if not cleaned_value:
        raise ValueError(f"{field_name} must not be empty.")

    return cleaned_value


def map_entry_to_person(entry: dict[str, Any]) -> Person:
    name = require_non_empty_string(entry.get("name"), "Person.name")
    surname = require_non_empty_string(entry.get("surname"), "Person.surname")
    city = require_non_empty_string(entry.get("city"), "Person.city")

    try:
        birth_year = int(entry.get("born"))
    except (TypeError, ValueError) as error:
        raise ValueError(f"Person.born must be an integer: {entry.get('born')!r}") from error
    
    return Person(
        name=name,
        surname=surname,
        birth_year=birth_year,
        city=city
    )


def extract_people_payload(raw_data: dict[str, Any]) -> list[Person]:
    payload_sent = raw_data.get("payload_sent")
    if not isinstance(payload_sent, dict):
        raise ValueError("Missing payload_sent object in people data.")
    
    answer = payload_sent.get("answer")
    if not isinstance(answer, list):
        raise ValueError("payload_sent.answer must be a list.")
    
    people: list[Person] = []

    for entry in answer:
        if not isinstance(entry, dict):
            raise ValueError(f"Each answer entry must be an object: {entry!r}")
        
        people.append(map_entry_to_person(entry))

    if not people:
        raise ValueError("payload_sent.answer does not contain any people records.")

    return people


def extract_unique_cities(people: list[Person]) -> list[str]:
    unique_cities: list[str] = []
    seen_cities: set[str] = set()

    for person in people:
        if person.city not in seen_cities:
            seen_cities.add(person.city)
            unique_cities.append(person.city)

    return unique_cities