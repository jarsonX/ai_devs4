# Deterministic extraction and relevance scoring for L21 materials.

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from src.apps.L21_radiomonitoring.models import EvidenceCandidate


PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d \-()]{6,}\d)(?!\d)")
AREA_RE = re.compile(r"\b(?:powierzchni\w*|area|obszar|km2|km²)\D{0,40}(\d+(?:[,.]\d+)?)", re.I)
WAREHOUSE_RE = re.compile(r"\b(?:magazyn\w*|warehouse\w*|skład\w*)\D{0,40}(\d{1,6})", re.I)
CITY_RE = re.compile(r"\b(?:miasto|city|nazwa)\D{0,30}([A-ZŁŚŻŹĆŃÓĄĘ][\wąćęłńóśżźĄĆĘŁŃÓŚŻŹ-]{2,})")
NOISE_MARKERS = ("bzzt", "bzzz", "ksh", "trzask", "szum", "pisk")
TASK_KEYWORDS = (
    "syjon",
    "miasto",
    "powierzchnia",
    "km2",
    "km²",
    "magazyn",
    "warehouse",
    "telefon",
    "kontakt",
    "zadzwoni",
)


# Normalize text for cheap keyword matching.
def normalize_text(value: str) -> str:
    text = value.strip().lower()
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


# Score one text fragment for task relevance.
def score_text_relevance(text: str) -> int:
    normalized = normalize_text(text)
    score = 0
    if "syjon" in normalized:
        score += 5
    if PHONE_RE.search(text):
        score += 5
    for keyword in ("miasto", "city", "kontakt", "telefon", "zadzwoni"):
        if keyword in normalized:
            score += 2
    for keyword in ("powierzchnia", "km2", "km²", "area", "obszar"):
        if keyword in normalized:
            score += 3
    for keyword in ("magazyn", "warehouse", "sklad"):
        if keyword in normalized:
            score += 3
    noise_hits = sum(normalized.count(marker) for marker in NOISE_MARKERS)
    if noise_hits >= 5 and score < 5:
        score -= 3
    return score


# Build deterministic evidence candidates from one text fragment.
def extract_candidates_from_text(
    text: str,
    *,
    source: str,
    method: str = "regex",
) -> list[EvidenceCandidate]:
    candidates: list[EvidenceCandidate] = []
    for match in PHONE_RE.finditer(text):
        candidates.append(
            EvidenceCandidate(
                field="phoneNumber",
                value=match.group(0).strip(),
                source=source,
                method=method,
                confidence="medium",
                note="Phone-like value found by regex.",
            )
        )

    for match in AREA_RE.finditer(text):
        candidates.append(
            EvidenceCandidate(
                field="cityArea",
                value=match.group(1).replace(",", "."),
                source=source,
                method=method,
                confidence="low",
                note="Area-like value found near area keyword.",
            )
        )

    for match in WAREHOUSE_RE.finditer(text):
        candidates.append(
            EvidenceCandidate(
                field="warehousesCount",
                value=match.group(1),
                source=source,
                method=method,
                confidence="low",
                note="Warehouse-like count found near warehouse keyword.",
            )
        )

    for match in CITY_RE.finditer(text):
        candidates.append(
            EvidenceCandidate(
                field="cityName",
                value=match.group(1).strip(),
                source=source,
                method=method,
                confidence="low",
                note="City-like name found near city keyword.",
            )
        )

    return candidates


# Recursively collect readable strings from arbitrary parsed data.
def collect_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(collect_strings(item))
        return strings
    if isinstance(value, dict):
        strings = []
        for key, nested in value.items():
            strings.append(str(key))
            strings.extend(collect_strings(nested))
        return strings
    if isinstance(value, (int, float)):
        return [str(value)]
    return []


# Build evidence candidates from parsed JSON or CSV records.
def extract_candidates_from_structured(
    value: Any,
    *,
    source: str,
) -> list[EvidenceCandidate]:
    candidates: list[EvidenceCandidate] = []
    serialized = json.dumps(value, ensure_ascii=False)
    candidates.extend(
        extract_candidates_from_text(
            serialized,
            source=source,
            method="structured_regex",
        )
    )

    lower_key_map = {}
    if isinstance(value, dict):
        lower_key_map = {str(key).lower(): nested for key, nested in value.items()}

    field_aliases = {
        "cityName": ("city", "cityname", "miasto", "nazwa", "name"),
        "cityArea": ("area", "cityarea", "powierzchnia", "km2", "km²"),
        "warehousesCount": ("warehouses", "warehousescount", "magazyny", "magazynow"),
        "phoneNumber": ("phone", "phonenumber", "telefon", "kontakt"),
    }
    for field, aliases in field_aliases.items():
        for alias in aliases:
            if alias in lower_key_map:
                candidates.append(
                    EvidenceCandidate(
                        field=field,  # type: ignore[arg-type]
                        value=str(lower_key_map[alias]),
                        source=source,
                        method="structured_key",
                        confidence="high",
                        note=f"Value found under structured key {alias}.",
                    )
                )
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                candidates.extend(_extract_candidates_from_city_record(item, source=source))
    return candidates


# Extract city and area candidates from one city-statistics record.
def _extract_candidates_from_city_record(
    record: dict[str, Any],
    *,
    source: str,
) -> list[EvidenceCandidate]:
    candidates: list[EvidenceCandidate] = []
    name = record.get("name")
    area = record.get("occupiedArea") or record.get("area") or record.get("cityArea")
    if isinstance(name, str) and name.strip():
        city_source = f"{source}:city:{name.strip()}"
        candidates.append(
            EvidenceCandidate(
                field="cityName",
                value=name.strip(),
                source=city_source,
                method="structured_city_record",
                confidence="medium",
                note="City name from city statistics record.",
            )
        )
        if area is not None:
            candidates.append(
                EvidenceCandidate(
                    field="cityArea",
                    value=str(area),
                    source=city_source,
                    method="structured_city_record",
                    confidence="high",
                    note="occupiedArea from the same city statistics record.",
                )
            )
    return candidates
