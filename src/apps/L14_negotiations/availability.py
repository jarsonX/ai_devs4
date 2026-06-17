# This module turns matched catalog items into compact Polish availability answers.

from __future__ import annotations

from dataclasses import dataclass

from .catalog_loader import Catalog, City, Item
from .matcher import MatchResult
from .query_interpreter import QueryInterpretation
from .schemas import MAX_OUTPUT_BYTES


SHORT_OUTPUT_FALLBACK = "Wynik za długi. Doprecyzuj zapytanie."
CITY_JOIN_SEPARATOR = ", "
ITEM_JOIN_SEPARATOR = "; "


# Represent availability facts for already accepted catalog matches.
@dataclass(frozen=True)
class AvailabilityResult:
    matched_items: tuple[Item, ...]
    unavailable_items: tuple[Item, ...]
    common_cities: tuple[City, ...]


# Map deterministic matcher failure codes to short Polish explanations.
def explain_match_failure(result: MatchResult) -> str:
    explanations = {
        "no_candidates": "brak kandydatów",
        "score_too_low": "za słabe dopasowanie",
        "ambiguous": "kilka podobnych produktów",
        "low_interpreter_confidence": "niepewny opis produktu",
        "missing_details": "brakuje szczegółów",
    }
    return explanations.get(result.reason, "brak bezpiecznego dopasowania")


# Pick a human-readable product label from the original phrase or interpreted type.
def describe_need(result: MatchResult) -> str:
    raw_fragment = result.need.raw_request_fragment.strip()
    if raw_fragment:
        return raw_fragment
    return result.need.normalized_product_type


# Return accepted catalog items in the same order as the requested needs.
def collect_matched_items(match_results: list[MatchResult]) -> tuple[Item, ...]:
    items: list[Item] = []
    for result in match_results:
        if result.accepted and result.best:
            items.append(result.best.item)
    return tuple(items)


# Compute the common available cities for all accepted items.
def resolve_availability(
    catalog: Catalog,
    match_results: list[MatchResult],
) -> AvailabilityResult:
    matched_items = collect_matched_items(match_results)
    unavailable_items = tuple(
        item for item in matched_items if item.code not in catalog.city_codes_by_item_code
    )

    if not matched_items or unavailable_items:
        return AvailabilityResult(
            matched_items=matched_items,
            unavailable_items=unavailable_items,
            common_cities=(),
        )

    common_city_codes = set(catalog.city_codes_by_item_code[matched_items[0].code])
    for item in matched_items[1:]:
        common_city_codes &= set(catalog.city_codes_by_item_code[item.code])

    common_cities = tuple(
        city for city in catalog.cities if city.code in common_city_codes
    )
    return AvailabilityResult(
        matched_items=matched_items,
        unavailable_items=unavailable_items,
        common_cities=common_cities,
    )


# Join names while preserving enough room for a short suffix when values are hidden.
def join_limited_values(
    values: tuple[str, ...],
    prefix: str,
    max_bytes: int,
) -> str:
    visible_values: list[str] = []
    hidden_count = 0

    for value in values:
        candidate_values = (*visible_values, value)
        hidden_after_candidate = len(values) - len(candidate_values)
        suffix = f" (+{hidden_after_candidate})" if hidden_after_candidate else ""
        candidate = prefix + CITY_JOIN_SEPARATOR.join(candidate_values) + suffix
        if len(candidate.encode("utf-8")) <= max_bytes:
            visible_values.append(value)
            hidden_count = hidden_after_candidate
            continue
        hidden_count = len(values) - len(visible_values)
        break

    if visible_values:
        suffix = f" (+{hidden_count})" if hidden_count else ""
        return prefix + CITY_JOIN_SEPARATOR.join(visible_values) + suffix

    hidden_suffix = f" (+{len(values)})" if values else ""
    candidate = prefix.rstrip() + hidden_suffix
    if len(candidate.encode("utf-8")) <= max_bytes:
        return candidate
    return SHORT_OUTPUT_FALLBACK


# Shorten matched item names only if an unusual catalog row threatens the byte limit.
def summarize_items(items: tuple[Item, ...], max_name_chars: int = 54) -> str:
    names = []
    for item in items:
        if len(item.name) <= max_name_chars:
            names.append(item.name)
        else:
            names.append(f"{item.name[: max_name_chars - 3]}...")
    return ITEM_JOIN_SEPARATOR.join(names)


# Keep a final safety net around every generated response.
def fit_output(output: str, fallback: str = SHORT_OUTPUT_FALLBACK) -> str:
    if len(output.encode("utf-8")) <= MAX_OUTPUT_BYTES:
        return output
    if len(fallback.encode("utf-8")) <= MAX_OUTPUT_BYTES:
        return fallback
    return fallback.encode("utf-8")[:MAX_OUTPUT_BYTES].decode("utf-8", errors="ignore")


# Build a compact Polish clarification response from interpreter uncertainty.
def build_clarification_output(interpretation: QueryInterpretation) -> str:
    reason = interpretation.clarification_reason or "doprecyzuj produkty"
    return fit_output(f"Doprecyzuj zapytanie: {reason}")


# Build a compact Polish response for deterministic matching failures.
def build_no_match_output(match_results: list[MatchResult]) -> str:
    failed_results = [result for result in match_results if not result.accepted]
    if not failed_results:
        return "Nie dopasowano produktów."

    result = failed_results[0]
    need_label = describe_need(result)
    reason = explain_match_failure(result)
    return fit_output(f"Nie dopasowano: {need_label} ({reason}). Doprecyzuj.")


# Build a compact Polish response after all products were matched.
def build_availability_output(availability: AvailabilityResult) -> str:
    matched_summary = summarize_items(availability.matched_items)

    if availability.unavailable_items:
        unavailable_summary = summarize_items(availability.unavailable_items)
        return fit_output(
            f"Dopasowano: {matched_summary}. Brak dostępności: {unavailable_summary}."
        )

    if not availability.common_cities:
        return fit_output(f"Dopasowano: {matched_summary}. Brak wspólnego miasta.")

    city_names = tuple(city.name for city in availability.common_cities)
    prefix = f"Dopasowano: {matched_summary}. Miasta: "
    return join_limited_values(city_names, prefix, MAX_OUTPUT_BYTES)


# Build the final tool output for the four public status families.
def build_tool_output(
    interpretation: QueryInterpretation,
    match_results: list[MatchResult],
    catalog: Catalog,
) -> str:
    if any(not result.accepted for result in match_results):
        if interpretation.needs_clarification:
            return build_clarification_output(interpretation)
        return build_no_match_output(match_results)

    availability = resolve_availability(catalog, match_results)
    return build_availability_output(availability)
