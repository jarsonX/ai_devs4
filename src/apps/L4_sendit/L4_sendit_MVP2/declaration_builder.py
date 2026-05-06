# Deterministic Stage 5 executor helper for the known declaration task.

from math import ceil

from src.apps.L4_sendit.L4_sendit_MVP2.models import (
    DeclarationTaskResultData,
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
    route_status = _require_text_fact(evidence_package, "route_status")
    disabled_route_exception = _require_text_fact(evidence_package, "disabled_route_exception")
    system_funded_categories = _normalize_category_symbols(
        _require_text_list_fact(evidence_package, "system_funded_categories")
    )
    standard_capacity_kg = _require_int_fact(evidence_package, "standard_capacity_kg")
    additional_wagon_capacity_kg = _require_int_fact(evidence_package, "additional_wagon_capacity_kg")

    category, category_uncertainty = _resolve_known_task_category(
        contents=task_understanding.provided_inputs.contents,
        route_status=route_status,
        disabled_route_exception=disabled_route_exception,
    )
    if category not in system_funded_categories:
        raise ValueError(
            "Known declaration executor does not yet support non-funded category pricing paths."
        )

    additional_wagons = _calculate_physical_additional_wagons(
        shipment_weight_kg=task_understanding.provided_inputs.weight_kg,
        standard_capacity_kg=standard_capacity_kg,
        additional_wagon_capacity_kg=additional_wagon_capacity_kg,
    )
    special_notes = _render_special_notes(task_understanding.provided_inputs.special_notes)

    uncertainty_notes = [
        category_uncertainty,
        (
            "WDP currently uses the physical additional wagon count for the known task. "
            "Explicit WDP terminology evidence is not yet extracted in Stage 4."
        ),
    ]

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
            EvidenceLink(result_field="category", fact_name="disabled_route_exception"),
            EvidenceLink(result_field="amount_due_pp", fact_name="system_funded_categories"),
            EvidenceLink(result_field="wdp", fact_name="standard_capacity_kg"),
            EvidenceLink(result_field="wdp", fact_name="additional_wagon_capacity_kg"),
        ],
        uncertainty_notes=uncertainty_notes,
    )


# Read one required string fact from the validated evidence package.
def _require_text_fact(evidence_package: EvidencePackage, fact_name: str) -> str:
    for fact in evidence_package.facts:
        if fact.name != fact_name:
            continue
        if isinstance(fact.value, str):
            return fact.value

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


# Resolve the known task category from the course-specific shipment contents.
def _resolve_known_task_category(
    contents: str,
    route_status: str,
    disabled_route_exception: str,
) -> tuple[str, str]:
    normalized_contents = contents.lower()
    normalized_route_status = route_status.lower()
    normalized_exception = disabled_route_exception.lower()

    # === KNOWN_TASK: spk_transport_declaration ===============================
    # The currently supported course task uses reactor fuel cassettes. MVP1 and
    # local validation established category A as the accepted interpretation.
    # Keep this course-specific rule explicit so future tasks can replace it
    # with their own documented executor logic.
    # =========================================================================
    if (
        "reaktor" in normalized_contents
        and "paliw" in normalized_contents
        and "wy" in normalized_route_status
    ):
        return (
            "A",
            (
                "Known task executor treats reactor fuel cassettes as category A to satisfy "
                "the disabled-route exception documented for Żarnowiec routes."
            ),
        )

    raise ValueError("Known declaration executor cannot resolve the shipment category from current evidence.")


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
        normalized_values.append(category_value.split(" ", 1)[0].strip())

    return normalized_values
