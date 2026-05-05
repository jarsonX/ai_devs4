# Local validation checks for the L4 sendit MVP1 pipeline.

from src.apps.L4_sendit.L4_sendit_MVP1.models import (
    DeclarationData,
    ShipmentCommand,
    StaticFacts,
    ValidationResult,
    WagonCalculation,
)


# === AI_BOUNDARY TODO ========================================================
# MVP2 should keep deterministic validation here, but may add AI-assisted
# uncertainty notes when document evidence conflicts or remains incomplete.
# =============================================================================
# Validate the parsed command, derived facts, wagon math, and declaration text.
def validate_run(
    command: ShipmentCommand,
    facts: StaticFacts,
    declaration_data: DeclarationData,
    wagon_calculation: WagonCalculation,
    declaration_text: str,
    template_text: str,
) -> list[ValidationResult]:
    results: list[ValidationResult] = []

    results.extend(_validate_command(command))
    results.extend(_validate_domain_decisions(facts, declaration_data))
    results.extend(_validate_wagon_calculation(command, facts, wagon_calculation))
    results.extend(_validate_declaration_text(declaration_data, declaration_text, template_text))
    results.append(
        ValidationResult(
            status="WARNING",
            message="WDP interpretation is uncertain and should stay visible until Hub verification.",
        )
    )

    return results


# Validate that the command contains the required shipment fields.
def _validate_command(command: ShipmentCommand) -> list[ValidationResult]:
    results: list[ValidationResult] = []

    required_text_fields = {
        "sender identifier": command.sender_identifier,
        "origin point": command.origin_point,
        "destination point": command.destination_point,
        "contents": command.contents,
        "special notes": command.special_notes,
    }
    missing_fields = [
        field_name for field_name, field_value in required_text_fields.items() if not field_value
    ]

    if missing_fields:
        results.append(
            ValidationResult(
                status="ERROR",
                message=f"command is missing required fields: {', '.join(missing_fields)}",
            )
        )
    else:
        results.append(ValidationResult(status="OK", message="command has required fields"))

    if command.weight_kg > 0:
        results.append(ValidationResult(status="OK", message="declared shipment weight is positive"))
    else:
        results.append(ValidationResult(status="ERROR", message="declared shipment weight is not positive"))

    if command.budget_pp == 0:
        results.append(ValidationResult(status="OK", message="budget is 0 PP as required"))
    else:
        results.append(ValidationResult(status="ERROR", message="budget is not 0 PP"))

    if command.special_notes.strip().lower() == "none":
        results.append(ValidationResult(status="OK", message="command asks for no special notes"))
    else:
        results.append(ValidationResult(status="ERROR", message="command contains special notes"))

    return results


# Validate route, category, and payment decisions for the known task facts.
def _validate_domain_decisions(
    facts: StaticFacts,
    declaration_data: DeclarationData,
) -> list[ValidationResult]:
    results: list[ValidationResult] = []

    if declaration_data.route_code == "X-01":
        results.append(ValidationResult(status="OK", message="route code X-01 is used"))
    else:
        results.append(ValidationResult(status="ERROR", message="route code is not X-01"))

    if facts.route_status == "disabled" and declaration_data.category in {"A", "B"}:
        results.append(
            ValidationResult(
                status="OK",
                message="closed route status is handled by an allowed category",
            )
        )
    else:
        results.append(
            ValidationResult(
                status="ERROR",
                message="closed route status is not handled by category A or B",
            )
        )

    if declaration_data.category == "A":
        results.append(ValidationResult(status="OK", message="category A is selected"))
    else:
        results.append(ValidationResult(status="ERROR", message="category A is not selected"))

    if declaration_data.amount_due_pp == 0:
        results.append(ValidationResult(status="OK", message="amount due is 0 PP"))
    else:
        results.append(ValidationResult(status="ERROR", message="amount due is not 0 PP"))

    return results


# Validate that the wagon calculation has enough capacity for the shipment.
def _validate_wagon_calculation(
    command: ShipmentCommand,
    facts: StaticFacts,
    wagon_calculation: WagonCalculation,
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    total_capacity_kg = (
        facts.standard_capacity_kg
        + wagon_calculation.physical_additional_wagons * facts.additional_wagon_capacity_kg
    )

    if wagon_calculation.physical_additional_wagons == 4:
        results.append(ValidationResult(status="OK", message="physical additional wagons equal 4"))
    else:
        results.append(
            ValidationResult(status="ERROR", message="physical additional wagons do not equal 4")
        )

    if total_capacity_kg >= command.weight_kg:
        results.append(
            ValidationResult(
                status="OK",
                message=f"total capacity {total_capacity_kg} kg covers {command.weight_kg} kg",
            )
        )
    else:
        results.append(
            ValidationResult(
                status="ERROR",
                message=f"total capacity {total_capacity_kg} kg is below {command.weight_kg} kg",
            )
        )

    if wagon_calculation.total_physical_wagons == 5:
        results.append(ValidationResult(status="OK", message="total physical wagons equal 5"))
    else:
        results.append(
            ValidationResult(status="ERROR", message="total physical wagons do not equal 5")
        )

    return results


# Validate the rendered declaration text against key template and task expectations.
def _validate_declaration_text(
    declaration_data: DeclarationData,
    declaration_text: str,
    template_text: str,
) -> list[ValidationResult]:
    results: list[ValidationResult] = []

    expected_fragments = [
        "SYSTEM PRZESYŁEK KONDUKTORSKICH - DEKLARACJA ZAWARTOŚCI",
        f"PUNKT NADAWCZY: {declaration_data.origin_point}",
        f"NADAWCA: {declaration_data.sender_identifier}",
        f"PUNKT DOCELOWY: {declaration_data.destination_point}",
        f"TRASA: {declaration_data.route_code}",
        f"KATEGORIA PRZESYŁKI: {declaration_data.category}",
        f"OPIS ZAWARTOŚCI (max 200 znaków): {declaration_data.contents}",
        f"DEKLAROWANA MASA (kg): {declaration_data.declared_weight_kg}",
        f"WDP: {declaration_data.wdp}",
        "UWAGI SPECJALNE: brak",
        f"KWOTA DO ZAPŁATY: {declaration_data.amount_due_pp} PP",
    ]
    missing_fragments = [
        fragment for fragment in expected_fragments if fragment not in declaration_text
    ]

    if missing_fragments:
        results.append(
            ValidationResult(
                status="ERROR",
                message=f"declaration is missing expected fragments: {len(missing_fragments)}",
            )
        )
    else:
        results.append(ValidationResult(status="OK", message="declaration has expected field values"))

    if _fragments_are_in_order(declaration_text, expected_fragments):
        results.append(ValidationResult(status="OK", message="declaration fields are in expected order"))
    else:
        results.append(ValidationResult(status="ERROR", message="declaration fields are out of order"))

    if "UWAGI SPECJALNE: brak" in declaration_text:
        results.append(ValidationResult(status="OK", message="no special operational notes are rendered"))
    else:
        results.append(ValidationResult(status="ERROR", message="special notes field is not rendered as brak"))

    if "Gdańsk" in declaration_text and "Żarnowiec" in declaration_text:
        results.append(ValidationResult(status="OK", message="Polish route values are preserved"))
    else:
        results.append(ValidationResult(status="ERROR", message="Polish route values are not preserved"))

    if "SYSTEM PRZESYŁEK KONDUKTORSKICH - DEKLARACJA ZAWARTOŚCI" in template_text:
        results.append(ValidationResult(status="OK", message="declaration template was loaded"))
    else:
        results.append(ValidationResult(status="ERROR", message="declaration template was not loaded"))

    return results


# Check that all fragments appear in the same order as the declaration template.
def _fragments_are_in_order(text: str, fragments: list[str]) -> bool:
    current_position = 0

    for fragment in fragments:
        next_position = text.find(fragment, current_position)
        if next_position == -1:
            return False

        current_position = next_position + len(fragment)

    return True
