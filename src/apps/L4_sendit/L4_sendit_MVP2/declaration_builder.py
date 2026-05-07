# Deterministic Stage 5 executor helper for the known declaration task.

from math import ceil

from src.apps.L4_sendit.L4_sendit_MVP2.models import (
    DeclarationTaskResultData,
    EvidenceFact,
    EvidenceLink,
    EvidencePackage,
    TaskResult,
    TaskUnderstanding,
)


# Build the known declaration task result from validated command inputs and evidence.
def build_declaration_task_result(
    task_understanding: TaskUnderstanding,
    evidence_package: EvidencePackage,
) -> TaskResult:
    route_code = _require_text_fact(evidence_package, "route_code")
    category, category_fact = _require_text_fact_with_context(evidence_package, "shipment_category")
    resolved_terms = _require_text_list_fact(evidence_package, "resolved_terms")
    system_funded_categories = _normalize_category_symbols(
        _require_text_list_fact(evidence_package, "system_funded_categories")
    )
    standard_capacity_kg = _require_int_fact(evidence_package, "standard_capacity_kg")
    additional_wagon_capacity_kg = _require_int_fact(evidence_package, "additional_wagon_capacity_kg")

    if category not in system_funded_categories:
        raise ValueError(
            "Known declaration executor does not yet support non-funded category pricing paths."
        )
    if not _term_list_contains_prefix(resolved_terms, "WDP"):
        raise ValueError("Known declaration executor requires resolved_terms evidence for WDP.")

    additional_wagons = _calculate_physical_additional_wagons(
        shipment_weight_kg=task_understanding.provided_inputs.weight_kg,
        standard_capacity_kg=standard_capacity_kg,
        additional_wagon_capacity_kg=additional_wagon_capacity_kg,
    )
    special_notes = _render_special_notes(task_understanding.provided_inputs.special_notes)

    uncertainty_notes = list(category_fact.uncertainty_notes)
    if category_fact.confidence < 1.0:
        uncertainty_notes.append(
            f"Shipment category evidence confidence is {category_fact.confidence:.2f} for fact shipment_category."
        )

    return TaskResult(
        task_name=task_understanding.task_name,
        result_kind="declaration_data",
        result=DeclarationTaskResultData(
            sender_identifier=task_understanding.provided_inputs.sender_identifier,
            origin_point=task_understanding.provided_inputs.origin_point,
            destination_point=task_understanding.provided_inputs.destination_point,
            route_code=route_code,
            category=category,
            contents=task_understanding.provided_inputs.contents,
            declared_weight_kg=task_understanding.provided_inputs.weight_kg,
            wdp=additional_wagons,
            special_notes=special_notes,
            amount_due_pp=0,
        ),
        evidence_links=[
            EvidenceLink(result_field="route_code", fact_name="route_code"),
            EvidenceLink(result_field="category", fact_name="shipment_category"),
            EvidenceLink(result_field="amount_due_pp", fact_name="system_funded_categories"),
            EvidenceLink(result_field="wdp", fact_name="standard_capacity_kg"),
            EvidenceLink(result_field="wdp", fact_name="additional_wagon_capacity_kg"),
            EvidenceLink(result_field="wdp", fact_name="resolved_terms"),
        ],
        uncertainty_notes=uncertainty_notes,
    )


# Read one required string fact from the validated evidence package.
def _require_text_fact(evidence_package: EvidencePackage, fact_name: str) -> str:
    fact_value, _ = _require_text_fact_with_context(evidence_package, fact_name)
    return fact_value


# Read one required string fact and keep the original evidence metadata.
def _require_text_fact_with_context(
    evidence_package: EvidencePackage,
    fact_name: str,
) -> tuple[str, EvidenceFact]:
    for fact in evidence_package.facts:
        if fact.name != fact_name:
            continue
        if isinstance(fact.value, str):
            return fact.value, fact

        raise ValueError(f"Evidence fact {fact_name} is not a string value.")

    raise ValueError(f"Required evidence fact is missing: {fact_name}")


# Read one required integer fact from the validated evidence package.
def _require_int_fact(evidence_package: EvidencePackage, fact_name: str) -> int:
    for fact in evidence_package.facts:
        if fact.name != fact_name:
            continue
        if isinstance(fact.value, int):
            return fact.value

        raise ValueError(f"Evidence fact {fact_name} is not an integer value.")

    raise ValueError(f"Required evidence fact is missing: {fact_name}")


# Read one required list-of-strings fact from the validated evidence package.
def _require_text_list_fact(evidence_package: EvidencePackage, fact_name: str) -> list[str]:
    for fact in evidence_package.facts:
        if fact.name != fact_name:
            continue
        if isinstance(fact.value, list) and all(isinstance(item, str) for item in fact.value):
            return list(fact.value)

        raise ValueError(f"Evidence fact {fact_name} is not a text list value.")

    raise ValueError(f"Required evidence fact is missing: {fact_name}")


# Calculate extra wagons needed after the standard train capacity is used.
def _calculate_physical_additional_wagons(
    shipment_weight_kg: int,
    standard_capacity_kg: int,
    additional_wagon_capacity_kg: int,
) -> int:
    remaining_weight_kg = shipment_weight_kg - standard_capacity_kg
    if remaining_weight_kg <= 0:
        return 0

    return ceil(remaining_weight_kg / additional_wagon_capacity_kg)


# Render the task result field without operational special notes.
def _render_special_notes(raw_special_notes: str) -> str:
    if raw_special_notes.strip().lower() == "none":
        return "brak"

    return raw_special_notes.strip()


# Normalize category evidence values such as "A - Strategiczna" into "A".
def _normalize_category_symbols(category_values: list[str]) -> list[str]:
    normalized_values: list[str] = []
    for category_value in category_values:
        normalized_values.append(_normalize_category_symbol(category_value))

    return normalized_values


# Normalize one category evidence value such as "A - Strategiczna" into "A".
def _normalize_category_symbol(category_value: str) -> str:
    return category_value.split(" ", 1)[0].strip()


# Check whether one resolved-terms fact contains a required term prefix such as WDP.
def _term_list_contains_prefix(term_entries: list[str], term_name: str) -> bool:
    normalized_prefix = f"{term_name.strip().upper()} ="
    return any(term_entry.strip().upper().startswith(normalized_prefix) for term_entry in term_entries)
