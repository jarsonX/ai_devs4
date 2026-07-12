# Deterministic parsing and validation for the shellaccess evidence chain.

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, timedelta


# Store the identifiers extracted from the matching timeline row.
@dataclass(frozen=True)
class TimelineMatch:
    found_date: date
    location_id: int
    entry_id: int


# Store the resolved GPS record used to cross-check the city mapping.
@dataclass(frozen=True)
class GpsMatch:
    latitude: float
    longitude: float
    place_type: str
    location_id: int
    entry_id: int


# Parse exactly one semicolon-delimited timeline record.
def parse_timeline_row(raw: str) -> TimelineMatch:
    rows = list(csv.reader(raw.splitlines(), delimiter=";"))
    if len(rows) != 1 or len(rows[0]) != 4:
        raise ValueError("Expected exactly one four-column timeline row.")
    raw_date, description, raw_location, raw_entry = rows[0]
    normalized = description.casefold()
    if "znaleziono ciało" not in normalized:
        raise ValueError("Timeline row does not describe the body being found.")
    return TimelineMatch(
        found_date=date.fromisoformat(raw_date),
        location_id=int(raw_location),
        entry_id=int(raw_entry),
    )


# Parse one plain-text city returned by jq -r.
def parse_city(raw: str) -> str:
    cities = [line.strip() for line in raw.splitlines() if line.strip()]
    if len(cities) != 1:
        raise ValueError("Expected exactly one city mapping.")
    return cities[0]


# Parse one tab-separated GPS mapping returned by jq -r.
def parse_gps(raw: str) -> GpsMatch:
    rows = [line.split("\t") for line in raw.splitlines() if line.strip()]
    if len(rows) != 1 or len(rows[0]) != 5:
        raise ValueError("Expected exactly one five-column GPS mapping.")
    latitude, longitude, place_type, location_id, entry_id = rows[0]
    return GpsMatch(
        latitude=float(latitude),
        longitude=float(longitude),
        place_type=place_type,
        location_id=int(location_id),
        entry_id=int(entry_id),
    )


# Build and cross-check the four-field answer required by the Hub.
def build_answer(timeline: TimelineMatch, city: str, gps: GpsMatch) -> dict[str, object]:
    if timeline.location_id != gps.location_id:
        raise ValueError("Timeline and GPS location identifiers do not match.")
    if timeline.entry_id != gps.entry_id:
        raise ValueError("Timeline and GPS entry identifiers do not match.")
    if not -90 <= gps.latitude <= 90 or not -180 <= gps.longitude <= 180:
        raise ValueError("GPS coordinates are outside valid ranges.")
    return {
        "date": (timeline.found_date - timedelta(days=1)).isoformat(),
        "city": city,
        "latitude": gps.latitude,
        "longitude": gps.longitude,
    }


# Quote the validated answer as one compact shell-safe echo command.
def build_submission_command(answer: dict[str, object]) -> str:
    encoded = json.dumps(answer, ensure_ascii=False, separators=(",", ":"))
    if "'" in encoded:
        raise ValueError("Answer contains a shell-unsafe apostrophe.")
    return f"echo '{encoded}'"
