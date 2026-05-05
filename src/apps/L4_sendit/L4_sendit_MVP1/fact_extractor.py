# Manual fact provider for the deterministic L4 sendit MVP1 stage.

from math import ceil

from src.apps.L4_sendit.L4_sendit_MVP1.models import (
    ShipmentCommand,
    StaticFacts,
    WagonCalculation,
)


# === AI_BOUNDARY TODO ========================================================
# MVP2 should extract route, category, funding, and WDP evidence from selected
# local references instead of returning manually confirmed task facts.
# =============================================================================
# Return manually confirmed task facts documented in the MVP1 README.
def load_static_facts() -> StaticFacts:
    return StaticFacts(
        route_code="X-01",
        route_status="disabled",
        disabled_route_exception="Routes around Żarnowiec may be used for category A or B shipments.",
        category="A",
        category_reason=(
            "Reactor fuel cassettes fit strategic transport, and the disabled "
            "Żarnowiec route requires category A or B."
        ),
        amount_due_pp=0,
        amount_due_reason="Category A shipments are funded by the System.",
        standard_capacity_kg=1000,
        additional_wagon_capacity_kg=500,
        wdp_meaning="paid additional wagons",
        wdp_uncertainty=(
            "MVP1 uses the physical additional wagon count as WDP and keeps this "
            "visible for later validation."
        ),
        evidence={
            "declaration_template": "data/L4_sendit/references/zalacznik-E.md",
            "route_code": "manually confirmed from data/L4_sendit/references/trasy-wylaczone.png",
            "route_status": "data/L4_sendit/references/trasy-wylaczone.png",
            "disabled_route_exception": "data/L4_sendit/references/index.md, Żarnowiec directive section",
            "system_funded_categories": "data/L4_sendit/references/index.md, fees section",
            "wagon_capacity": "data/L4_sendit/references/dodatkowe-wagony.md",
            "wdp_meaning": "data/L4_sendit/references/zalacznik-G.md",
        },
    )


# Calculate extra wagons needed after the standard train capacity is used.
def calculate_physical_additional_wagons(
    command: ShipmentCommand,
    facts: StaticFacts,
) -> int:
    remaining_weight_kg = command.weight_kg - facts.standard_capacity_kg
    if remaining_weight_kg <= 0:
        return 0

    return ceil(remaining_weight_kg / facts.additional_wagon_capacity_kg)


# Explain the wagon calculation with intermediate values.
def calculate_wagon_details(
    command: ShipmentCommand,
    facts: StaticFacts,
) -> WagonCalculation:
    remaining_weight_kg = max(command.weight_kg - facts.standard_capacity_kg, 0)
    physical_additional_wagons = calculate_physical_additional_wagons(command, facts)
    total_physical_wagons = 1 + physical_additional_wagons

    return WagonCalculation(
        shipment_weight_kg=command.weight_kg,
        standard_capacity_kg=facts.standard_capacity_kg,
        remaining_weight_kg=remaining_weight_kg,
        additional_wagon_capacity_kg=facts.additional_wagon_capacity_kg,
        physical_additional_wagons=physical_additional_wagons,
        total_physical_wagons=total_physical_wagons,
    )
