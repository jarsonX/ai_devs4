# Deterministic validation for the L4 sendit MVP2 AI command parser output.

from src.apps.L4_sendit.L4_sendit_MVP2.models import (
    CommandValidationResult,
    ParsedCommand,
    ReferenceInventoryItem,
    SelectedSources,
)


# Validate model output before it can be projected into the deterministic pipeline.
def validate_parsed_command(command: ParsedCommand) -> list[CommandValidationResult]:
    results: list[CommandValidationResult] = []

    results.extend(_validate_required_text(command))
    results.extend(_validate_normalized_values(command))
    results.extend(_validate_lists(command))
    results.extend(_validate_known_stage_1_expectations(command))

    return results


# Validate selected sources before any downstream extraction stage can use them.
def validate_selected_sources(
    selected_sources: SelectedSources,
    inventory: list[ReferenceInventoryItem],
) -> list[CommandValidationResult]:
    results: list[CommandValidationResult] = []
    inventory_by_path = {item.path: item for item in inventory}

    results.extend(_validate_selected_source_paths(selected_sources, inventory_by_path))
    results.extend(_validate_rejected_source_paths(selected_sources, inventory_by_path))
    results.extend(_validate_required_source_categories(selected_sources))
    results.extend(_validate_source_selection_lists(selected_sources))

    return results


# Raise a clear error when source selection validation has blocking errors.
def raise_if_source_selection_invalid(validation_results: list[CommandValidationResult]) -> None:
    error_messages = [
        validation_result.message
        for validation_result in validation_results
        if validation_result.status == "ERROR"
    ]
    if error_messages:
        raise ValueError(f"AI source selector output failed validation: {', '.join(error_messages)}")


# Validate that required text fields are populated after schema parsing.
def _validate_required_text(command: ParsedCommand) -> list[CommandValidationResult]:
    required_text_fields = {
        "sender_identifier": command.sender_identifier,
        "origin_point": command.origin_point,
        "destination_point": command.destination_point,
        "contents": command.contents,
        "special_notes": command.special_notes,
    }
    missing_fields = [
        field_name for field_name, field_value in required_text_fields.items() if not field_value.strip()
    ]

    if missing_fields:
        return [
            CommandValidationResult(
                status="ERROR",
                message=f"parsed command has empty required fields: {', '.join(missing_fields)}",
            )
        ]

    return [CommandValidationResult(status="OK", message="parsed command has required text fields")]


# Validate selected source paths and source types against the deterministic inventory.
def _validate_selected_source_paths(
    selected_sources: SelectedSources,
    inventory_by_path: dict[str, ReferenceInventoryItem],
) -> list[CommandValidationResult]:
    results: list[CommandValidationResult] = []
    seen_paths: set[str] = set()

    for source in selected_sources.selected_sources:
        if source.path in seen_paths:
            results.append(
                CommandValidationResult(
                    status="ERROR",
                    message=f"selected source is duplicated: {source.path}",
                )
            )
        seen_paths.add(source.path)

        inventory_item = inventory_by_path.get(source.path)
        if inventory_item is None:
            results.append(
                CommandValidationResult(
                    status="ERROR",
                    message=f"selected source is not in local inventory: {source.path}",
                )
            )
            continue

        if source.source_type == inventory_item.source_type:
            results.append(
                CommandValidationResult(
                    status="OK",
                    message=f"selected source type matches inventory: {source.path}",
                )
            )
        else:
            results.append(
                CommandValidationResult(
                    status="ERROR",
                    message=f"selected source type mismatch: {source.path}",
                )
            )

    if selected_sources.selected_sources:
        results.append(CommandValidationResult(status="OK", message="source selector selected at least one source"))
    else:
        results.append(CommandValidationResult(status="ERROR", message="source selector selected no sources"))

    return results


# Validate rejected source paths because rejected entries are model output too.
def _validate_rejected_source_paths(
    selected_sources: SelectedSources,
    inventory_by_path: dict[str, ReferenceInventoryItem],
) -> list[CommandValidationResult]:
    unknown_rejected_paths = [
        rejected_source.path
        for rejected_source in selected_sources.rejected_sources
        if rejected_source.path not in inventory_by_path
    ]
    if unknown_rejected_paths:
        return [
            CommandValidationResult(
                status="ERROR",
                message=f"rejected source paths are not in local inventory: {', '.join(unknown_rejected_paths)}",
            )
        ]

    return [CommandValidationResult(status="OK", message="rejected source paths match local inventory")]


# Validate that the current workflow has all categories needed by later stages.
def _validate_required_source_categories(
    selected_sources: SelectedSources,
) -> list[CommandValidationResult]:
    selected_paths = {source.path for source in selected_sources.selected_sources}
    required_sources = {
        "declaration template": "data/L4_sendit/references/zalacznik-E.md",
        "broad SPK rules": "data/L4_sendit/references/index.md",
        "disabled route evidence": "data/L4_sendit/references/trasy-wylaczone.png",
        "wagon capacity": "data/L4_sendit/references/dodatkowe-wagony.md",
        "WDP meaning": "data/L4_sendit/references/zalacznik-G.md",
    }
    missing_categories = [
        category
        for category, required_path in required_sources.items()
        if required_path not in selected_paths
    ]

    if missing_categories:
        return [
            CommandValidationResult(
                status="ERROR",
                message=f"source selection misses required categories: {', '.join(missing_categories)}",
            )
        ]

    return [CommandValidationResult(status="OK", message="source selection covers required categories")]


# Validate list fields that preserve uncertainty instead of guessing.
def _validate_source_selection_lists(selected_sources: SelectedSources) -> list[CommandValidationResult]:
    results: list[CommandValidationResult] = []

    if selected_sources.missing_sources:
        results.append(
            CommandValidationResult(
                status="ERROR",
                message=f"model reported missing source needs: {', '.join(selected_sources.missing_sources)}",
            )
        )
    else:
        results.append(CommandValidationResult(status="OK", message="model reported no missing source needs"))

    if selected_sources.uncertainty_notes:
        results.append(
            CommandValidationResult(
                status="WARNING",
                message=f"model reported source selection uncertainty notes: {len(selected_sources.uncertainty_notes)}",
            )
        )
    else:
        results.append(CommandValidationResult(status="OK", message="model reported no source selection uncertainty"))

    return results


# Validate normalized numeric values and confidence range.
def _validate_normalized_values(command: ParsedCommand) -> list[CommandValidationResult]:
    results: list[CommandValidationResult] = []

    if command.weight_kg > 0:
        results.append(CommandValidationResult(status="OK", message="weight_kg is a positive integer"))
    else:
        results.append(CommandValidationResult(status="ERROR", message="weight_kg must be positive"))

    if command.budget_pp >= 0:
        results.append(CommandValidationResult(status="OK", message="budget_pp is a non-negative integer"))
    else:
        results.append(CommandValidationResult(status="ERROR", message="budget_pp must be non-negative"))

    if 0.0 <= command.confidence <= 1.0:
        results.append(CommandValidationResult(status="OK", message="confidence is within 0.0-1.0"))
    else:
        results.append(CommandValidationResult(status="ERROR", message="confidence is outside 0.0-1.0"))

    return results


# Validate uncertainty fields that protect downstream code from silent guessing.
def _validate_lists(command: ParsedCommand) -> list[CommandValidationResult]:
    results: list[CommandValidationResult] = []

    if command.missing_fields:
        results.append(
            CommandValidationResult(
                status="ERROR",
                message=f"model reported missing command fields: {', '.join(command.missing_fields)}",
            )
        )
    else:
        results.append(CommandValidationResult(status="OK", message="model reported no missing fields"))

    if command.uncertainty_notes:
        results.append(
            CommandValidationResult(
                status="WARNING",
                message=f"model reported uncertainty notes: {len(command.uncertainty_notes)}",
            )
        )
    else:
        results.append(CommandValidationResult(status="OK", message="model reported no parsing uncertainty"))

    return results


# Validate known Stage 1 command expectations without adding route reasoning.
def _validate_known_stage_1_expectations(command: ParsedCommand) -> list[CommandValidationResult]:
    results: list[CommandValidationResult] = []

    if command.sender_identifier == "450202122":
        results.append(CommandValidationResult(status="OK", message="sender identifier matches command"))
    else:
        results.append(CommandValidationResult(status="ERROR", message="sender identifier does not match command"))

    if command.origin_point == "Gdańsk":
        results.append(CommandValidationResult(status="OK", message="origin point matches command"))
    else:
        results.append(CommandValidationResult(status="ERROR", message="origin point does not match command"))

    if command.destination_point == "Żarnowiec":
        results.append(CommandValidationResult(status="OK", message="destination point matches command"))
    else:
        results.append(CommandValidationResult(status="ERROR", message="destination point does not match command"))

    if command.weight_kg == 2800:
        results.append(CommandValidationResult(status="OK", message="weight is normalized to 2800 kg"))
    else:
        results.append(CommandValidationResult(status="ERROR", message="weight is not normalized to 2800 kg"))

    if command.budget_pp == 0:
        results.append(CommandValidationResult(status="OK", message="budget is normalized to 0 PP"))
    else:
        results.append(CommandValidationResult(status="ERROR", message="budget is not normalized to 0 PP"))

    if command.special_notes.strip().lower() == "none":
        results.append(CommandValidationResult(status="OK", message="special notes are normalized to none"))
    else:
        results.append(CommandValidationResult(status="ERROR", message="special notes are not normalized to none"))

    if command.contents == "kasety z paliwem do reaktora":
        results.append(CommandValidationResult(status="OK", message="contents match command"))
    else:
        results.append(CommandValidationResult(status="ERROR", message="contents do not match command"))

    return results
