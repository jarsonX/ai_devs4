# Human-readable run report builder for the L4 sendit MVP1 pipeline.

from src.apps.L4_sendit.L4_sendit_MVP1.models import (
    DeclarationData,
    ShipmentCommand,
    StaticFacts,
    ValidationResult,
    WagonCalculation,
)


# Build a short markdown report that explains the deterministic MVP1 run.
def build_run_report(
    command: ShipmentCommand,
    facts: StaticFacts,
    declaration_data: DeclarationData,
    wagon_calculation: WagonCalculation,
    validation_results: list[ValidationResult],
    loaded_references: list[str],
) -> str:
    return "\n".join(
        [
            "# L4 Sendit MVP1 Run Report",
            "",
            "## Parsed Command",
            "",
            f"- Sender identifier: `{command.sender_identifier}`",
            f"- Origin point: `{command.origin_point}`",
            f"- Destination point: `{command.destination_point}`",
            f"- Weight: `{command.weight_kg} kg`",
            f"- Budget: `{command.budget_pp} PP`",
            f"- Contents: `{command.contents}`",
            f"- Special notes: `{command.special_notes}`",
            "",
            "## Loaded References",
            "",
            *[f"- `{reference}`" for reference in loaded_references],
            "",
            "## Derived Facts",
            "",
            f"- Route code: `{facts.route_code}`",
            f"- Route status: `{facts.route_status}`",
            f"- Selected category: `{facts.category}`",
            f"- Amount due: `{facts.amount_due_pp} PP`",
            f"- Declaration WDP: `{declaration_data.wdp}`",
            "",
            "## Wagon Calculation",
            "",
            f"- Shipment weight: `{wagon_calculation.shipment_weight_kg} kg`",
            f"- Standard train capacity: `{wagon_calculation.standard_capacity_kg} kg`",
            f"- Remaining weight: `{wagon_calculation.remaining_weight_kg} kg`",
            f"- Additional wagon capacity: `{wagon_calculation.additional_wagon_capacity_kg} kg`",
            f"- Physical additional wagons: `{wagon_calculation.physical_additional_wagons}`",
            f"- Total physical wagons: `{wagon_calculation.total_physical_wagons}`",
            "",
            "## Validation",
            "",
            *[
                f"- {validation_result.status}: {validation_result.message}"
                for validation_result in validation_results
            ],
            "",
            "## Closed Route Reasoning",
            "",
            (
                f"Route `{facts.route_code}` is disabled, but the documented exception "
                f"allows this route for category A or B shipments. MVP1 selects "
                f"category `{facts.category}` because {facts.category_reason}"
            ),
            "",
            "## Uncertainty",
            "",
            facts.wdp_uncertainty,
            "",
            "## AI Boundary",
            "",
            "- MVP1 uses a fixed-format command parser instead of AI command understanding.",
            "- MVP1 uses manually confirmed facts instead of AI source selection or extraction.",
            "- MVP1 does not use vision/OCR for `trasy-wylaczone.png`; route `X-01` is explicit.",
            "- MVP1 keeps WDP uncertainty visible instead of resolving it with model reasoning.",
            "- MVP2 may add AI only as bounded, inspectable components with validation.",
        ]
    )
