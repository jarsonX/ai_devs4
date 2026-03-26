"""Small shared data models for the EDU1 app."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Person:
    """Normalized person record extracted from the people payload."""

    name: str
    surname: str
    birth_year: int
    city: str


@dataclass(frozen=True)
class FinalResult:
    """Final business result produced by the EDU1 pipeline."""

    selected_city: str
    person: Person
    access_level: int
