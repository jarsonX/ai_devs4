from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersonRecord:
    name: str
    surname: str
    gender: str
    birth_date: str
    birth_place: str
    job: str