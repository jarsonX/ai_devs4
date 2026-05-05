# Human-readable run report builder for the L4 sendit MVP2 Stage 1-2 pipeline.

from src.apps.L4_sendit.L4_sendit_MVP1.models import (
    DeclarationData,
    StaticFacts,
    ValidationResult,
    WagonCalculation,
)
from src.apps.L4_sendit.L4_sendit_MVP2.models import (
    CommandValidationResult,
    ParsedCommand,
    ReferenceInventoryItem,
    SelectedSources,
)


# Build a short markdown report explaining AI parsing and deterministic validation.
def build_run_report(
    parsed_command: ParsedCommand,
    command_validation_results: list[CommandValidationResult],
    facts: StaticFacts,
    declaration_data: DeclarationData,
    wagon_calculation: WagonCalculation,
    validation_results: list[ValidationResult],
    reference_inventory: list[ReferenceInventoryItem],
    selected_sources: SelectedSources,
    source_selection_validation_results: list[CommandValidationResult],
    loaded_references: list[str],
    model_source: str,
    source_selection_model_source: str,
) -> str:
    return "\n".join(
        [
            "# L4 Sendit MVP2 Run Report",
            "",
            "## Stage 1 AI Command Parser",
            "",
            f"- Model source: `{model_source}`",
            f"- Sender identifier: `{parsed_command.sender_identifier}`",
            f"- Origin point: `{parsed_command.origin_point}`",
            f"- Destination point: `{parsed_command.destination_point}`",
            f"- Weight: `{parsed_command.weight_kg} kg`",
            f"- Budget: `{parsed_command.budget_pp} PP`",
            f"- Contents: `{parsed_command.contents}`",
            f"- Special notes: `{parsed_command.special_notes}`",
            f"- Confidence: `{parsed_command.confidence}`",
            f"- Missing fields: `{', '.join(parsed_command.missing_fields) or 'none'}`",
            f"- Uncertainty notes: `{', '.join(parsed_command.uncertainty_notes) or 'none'}`",
            "",
            "## Command Parser Validation",
            "",
            *[
                f"- {validation_result.status}: {validation_result.message}"
                for validation_result in command_validation_results
            ],
            "",
            "## Stage 2 Source Selection",
            "",
            f"- Model source: `{source_selection_model_source}`",
            f"- Inventory files: `{len(reference_inventory)}`",
            f"- Selected sources: `{len(selected_sources.selected_sources)}`",
            f"- Rejected sources: `{len(selected_sources.rejected_sources)}`",
            f"- Missing sources: `{', '.join(selected_sources.missing_sources) or 'none'}`",
            f"- Uncertainty notes: `{', '.join(selected_sources.uncertainty_notes) or 'none'}`",
            "",
            "### Selected Sources",
            "",
            *[
                (
                    f"- `{source.path}` ({source.source_type}, {source.intended_use}, "
                    f"confidence `{source.confidence}`): {source.reason}"
                )
                for source in selected_sources.selected_sources
            ],
            "",
            "### Source Selection Validation",
            "",
            *[
                f"- {validation_result.status}: {validation_result.message}"
                for validation_result in source_selection_validation_results
            ],
            "",
            "## Loaded References",
            "",
            *[f"- `{reference}`" for reference in loaded_references],
            "",
            "## Deterministic MVP1-Compatible Pipeline",
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
            "## Pipeline Validation",
            "",
            *[
                f"- {validation_result.status}: {validation_result.message}"
                for validation_result in validation_results
            ],
            "",
            "## AI Boundary",
            "",
            "- MVP2 Stage 1 uses AI only to parse the operational command.",
            "- MVP2 Stage 2 uses AI only to select local reference sources from a deterministic inventory.",
            "- Fact extraction, route reasoning, declaration rendering, and Hub submission remain deterministic or outside the current AI boundary.",
            "- Model output is saved for inspection and used only after schema plus semantic validation passes.",
        ]
    )
