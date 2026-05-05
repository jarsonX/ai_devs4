# Deterministic validation for the L4 sendit MVP2 AI command parser output.

from src.apps.L4_sendit.L4_sendit_MVP2.models import (
    CommandValidationResult,
    ParsedCommand,
)


# Validate model output before it can be projected into the deterministic pipeline.
def validate_parsed_command(command: ParsedCommand) -> list[CommandValidationResult]:
    results: list[CommandValidationResult] = []

    results.extend(_validate_required_text(command))
    results.extend(_validate_normalized_values(command))
    results.extend(_validate_lists(command))
    results.extend(_validate_known_stage_1_expectations(command))

    return results


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
