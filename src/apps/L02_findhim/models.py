"""This file keeps the small data models used across the app, like suspects, plants, and answers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Suspect:
    name: str
    surname: str
    birth_year: int


@dataclass(frozen=True)
class PowerPlantRecord:
    city: str
    normalized_city: str
    code: str
    is_active: bool
    power: str


@dataclass(frozen=True)
class CityCoordinates:
    city: str
    normalized_city: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class PowerPlantCity:
    city: str
    normalized_city: str
    code: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class PersonLocation:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class CandidateDistance:
    suspect: Suspect
    power_plant_code: str
    power_plant_city: str
    distance_km: float
    observed_latitude: float
    observed_longitude: float


@dataclass(frozen=True)
class VerificationAnswer:
    name: str
    surname: str
    accessLevel: int
    powerPlant: str
