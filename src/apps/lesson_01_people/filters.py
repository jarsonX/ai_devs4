from __future__ import annotations

from .models import PersonRecord


CURRENT_YEAR = 2026
MIN_AGE = 20
MAX_AGE = 40
TARGET_GENDER = "M"
TARGET_BIRTH_PLACE = "Grudziądz"


def extract_birth_year(birth_date: str) -> int:
    return int(birth_date[:4])


def calculate_age(birth_year: int, current_year: int = CURRENT_YEAR) -> int:
    return current_year - birth_year


def is_male(person: PersonRecord) -> bool:
    return person.gender.upper() == TARGET_GENDER


def is_born_in_target_place(person: PersonRecord) -> bool:
    return person.birth_place == TARGET_BIRTH_PLACE


def is_age_in_range(person: PersonRecord) -> bool:
    birth_year = extract_birth_year(person.birth_date)
    age = calculate_age(birth_year)
    return MIN_AGE <= age <= MAX_AGE


def matches_initial_criteria(person: PersonRecord) -> bool:
    return (
        is_male(person)
        and is_born_in_target_place(person)
        and is_age_in_range(person)
    )


def filter_people_for_transport_check(people: list[PersonRecord]) -> list[PersonRecord]:
    return [person for person in people if matches_initial_criteria(person)]