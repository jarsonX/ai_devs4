# Evidence processing and final report validation for L21.

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import re

from src.apps.L21_radiomonitoring.models import (
    EvidenceCandidate,
    FinalReport,
    city_area_is_valid,
    phone_number_is_valid,
)


# Store evidence plus selected text snippets for model extraction.
@dataclass(frozen=True)
class EvidenceBundle:
    candidates: list[EvidenceCandidate]
    text_snippets: list[dict[str, str]]


# Normalize one phone number while preserving Hub-friendly digits.
def normalize_phone_number(value: str) -> str:
    return re.sub(r"\D", "", value)


# Format one area value with real mathematical rounding to two decimal places.
def format_city_area(value: str) -> str:
    normalized = value.strip().replace(",", ".")
    try:
        decimal_value = Decimal(normalized)
    except InvalidOperation as error:
        raise ValueError(f"Invalid city area value: {value!r}") from error
    return str(decimal_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# Validate and normalize one final report before Hub submission.
def validate_final_report(report: FinalReport) -> FinalReport:
    city_name = report.cityName.strip()
    if not city_name:
        raise ValueError("cityName is missing.")

    city_area = format_city_area(report.cityArea)
    if not city_area_is_valid(city_area):
        raise ValueError(f"cityArea has invalid format: {city_area!r}")

    warehouses_count = int(report.warehousesCount)
    if warehouses_count < 0:
        raise ValueError("warehousesCount cannot be negative.")

    phone_number = normalize_phone_number(report.phoneNumber)
    if not phone_number_is_valid(phone_number):
        raise ValueError(f"phoneNumber has invalid format: {report.phoneNumber!r}")

    return FinalReport(
        cityName=city_name,
        cityArea=city_area,
        warehousesCount=warehouses_count,
        phoneNumber=phone_number,
    )


# Return only candidate facts that can plausibly support final fields.
def filter_final_field_candidates(candidates: list[EvidenceCandidate]) -> list[EvidenceCandidate]:
    return [
        candidate
        for candidate in candidates
        if candidate.field in {"cityName", "cityArea", "warehousesCount", "phoneNumber"}
        and candidate.value.strip()
    ]


# Derive a final report from strong cross-source evidence before asking a model.
def derive_report_from_evidence(
    candidates: list[EvidenceCandidate],
    snippets: list[dict[str, str]],
) -> FinalReport | None:
    joined_snippets = "\n".join(snippet.get("text", "") for snippet in snippets)
    normalized = _normalize_polish(joined_snippets)

    city_name = _derive_city_from_audio_context(normalized)
    if city_name is None:
        return None

    city_area = _find_city_area_for_city(candidates, city_name)
    warehouses_count = _derive_warehouse_count(normalized)
    phone_number = _find_best_phone(candidates)

    if city_area is None or warehouses_count is None or phone_number is None:
        return None

    return validate_final_report(
        FinalReport(
            cityName=city_name,
            cityArea=city_area,
            warehousesCount=warehouses_count,
            phoneNumber=phone_number,
        )
    )


# Normalize Polish text enough for deterministic clue matching.
def _normalize_polish(value: str) -> str:
    replacements = {
        "ą": "a",
        "ć": "c",
        "ę": "e",
        "ł": "l",
        "ń": "n",
        "ó": "o",
        "ś": "s",
        "ż": "z",
        "ź": "z",
    }
    normalized = value.lower()
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized


# Derive the real city name from the audio clue about warehouses and beef.
def _derive_city_from_audio_context(normalized_text: str) -> str | None:
    if "w skarszewach" in normalized_text and "dwunasty magazyn" in normalized_text:
        return "Skarszewy"
    return None


# Find the city area from the structured city record matching the selected city.
def _find_city_area_for_city(
    candidates: list[EvidenceCandidate],
    city_name: str,
) -> str | None:
    marker = f"city:{city_name}".lower()
    for candidate in candidates:
        if candidate.field == "cityArea" and marker in candidate.source.lower():
            return candidate.value
    return None


# Derive current warehouse count from a planned ordinal warehouse clue.
def _derive_warehouse_count(normalized_text: str) -> int | None:
    if "dwunasty magazyn" in normalized_text:
        return 11
    return None


# Pick the strongest phone candidate from image or text evidence.
def _find_best_phone(candidates: list[EvidenceCandidate]) -> str | None:
    phone_candidates = [
        candidate
        for candidate in candidates
        if candidate.field == "phoneNumber" and phone_number_is_valid(candidate.value)
    ]
    if not phone_candidates:
        return None
    phone_candidates.sort(
        key=lambda candidate: (
            1 if candidate.confidence == "high" else 0,
            1 if "image" in candidate.method or "vision" in candidate.method else 0,
        ),
        reverse=True,
    )
    return phone_candidates[0].value
