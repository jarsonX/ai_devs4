# Declaration rendering for the L4 sendit MVP1 learning app.

from datetime import date

from src.apps.L4_sendit.L4_sendit_MVP1.fact_extractor import (
    calculate_physical_additional_wagons,
)
from src.apps.L4_sendit.L4_sendit_MVP1.models import (
    DeclarationData,
    ShipmentCommand,
    StaticFacts,
)


# Combine parsed command fields and static facts into render-ready data.
def build_declaration_data(
    command: ShipmentCommand,
    facts: StaticFacts,
    declaration_date: date | None = None,
) -> DeclarationData:
    selected_date = declaration_date or date.today()
    additional_wagons = calculate_physical_additional_wagons(command, facts)

    return DeclarationData(
        declaration_date=selected_date.isoformat(),
        sender_identifier=command.sender_identifier,
        origin_point=command.origin_point,
        destination_point=command.destination_point,
        route_code=facts.route_code,
        category=facts.category,
        contents=command.contents,
        declared_weight_kg=command.weight_kg,
        wdp=additional_wagons,
        special_notes=_render_special_notes(command.special_notes),
        amount_due_pp=facts.amount_due_pp,
    )


# Render the Stage 1 declaration in the exact field order from the template.
def render_declaration(data: DeclarationData, template_text: str) -> str:
    _ = template_text

    return "\n".join(
        [
            "SYSTEM PRZESYŁEK KONDUKTORSKICH - DEKLARACJA ZAWARTOŚCI",
            "======================================================",
            f"DATA: {data.declaration_date}",
            f"PUNKT NADAWCZY: {data.origin_point}",
            "------------------------------------------------------",
            f"NADAWCA: {data.sender_identifier}",
            f"PUNKT DOCELOWY: {data.destination_point}",
            f"TRASA: {data.route_code}",
            "------------------------------------------------------",
            f"KATEGORIA PRZESYŁKI: {data.category}",
            "------------------------------------------------------",
            f"OPIS ZAWARTOŚCI (max 200 znaków): {data.contents}",
            "------------------------------------------------------",
            f"DEKLAROWANA MASA (kg): {data.declared_weight_kg}",
            "------------------------------------------------------",
            f"WDP: {data.wdp}",
            "------------------------------------------------------",
            f"UWAGI SPECJALNE: {data.special_notes}",
            "------------------------------------------------------",
            f"KWOTA DO ZAPŁATY: {data.amount_due_pp} PP",
            "------------------------------------------------------",
            "OŚWIADCZAM, ŻE PODANE INFORMACJE SĄ PRAWDZIWE.",
            "BIORĘ NA SIEBIE KONSEKWENCJĘ ZA FAŁSZYWE OŚWIADCZENIE.",
            "======================================================",
        ]
    )


# Render the template field without adding operational special notes.
def _render_special_notes(raw_special_notes: str) -> str:
    if raw_special_notes.strip().lower() == "none":
        return "brak"

    return raw_special_notes.strip()
