# Validation helpers for model-proposed drone instruction plans.

from __future__ import annotations

import re
from dataclasses import dataclass

from src.apps.L10_drone.config import MissionConfig, RuntimeConfig
from src.apps.L10_drone.planner import DroneInstructionPlan


DESTINATION_PATTERN = re.compile(r"^setDestinationObject\((?P<object_id>[^)]+)\)$")


# Preserve local validation results in a log-friendly structure.
@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    issues: list[str]


# Check one planner output before it can be submitted to the Hub.
def validate_instruction_plan(
    plan: DroneInstructionPlan,
    runtime: RuntimeConfig,
    *,
    mission: MissionConfig | None = None,
    secret_values: list[str] | None = None,
    previous_instructions: list[str] | None = None,
) -> ValidationResult:
    issues: list[str] = []
    secrets = [value for value in (secret_values or []) if value]

    if len(plan.instructions) > runtime.max_instructions:
        issues.append(
            f"instructions list exceeds {runtime.max_instructions} items."
        )

    for index, instruction in enumerate(plan.instructions, start=1):
        if len(instruction) > runtime.max_instruction_chars:
            issues.append(
                f"instruction {index} exceeds {runtime.max_instruction_chars} characters."
            )
        lowered = instruction.lower()
        if "apikey" in lowered or "api_key" in lowered:
            issues.append(f"instruction {index} contains an API key field name.")
        for secret in secrets:
            if secret and secret in instruction:
                issues.append(f"instruction {index} contains a configured secret value.")

    if mission is not None:
        issues.extend(_validate_mission_instructions(plan, mission))

    if len(plan.change_summary) > runtime.max_change_summary_chars:
        issues.append(
            f"change_summary exceeds {runtime.max_change_summary_chars} characters."
        )

    if previous_instructions is not None and plan.instructions == previous_instructions:
        issues.append("repair repeated the exact previous instruction list.")

    return ValidationResult(passed=not issues, issues=issues)


# Check mission-specific facts learned from the task and first Hub feedback.
def _validate_mission_instructions(
    plan: DroneInstructionPlan,
    mission: MissionConfig,
) -> list[str]:
    issues: list[str] = []
    destination_objects: list[str] = []

    for instruction in plan.instructions:
        match = DESTINATION_PATTERN.match(instruction)
        if match:
            destination_objects.append(match.group("object_id").strip())

    expected_destination = mission.power_plant_code
    if not destination_objects:
        issues.append(
            f"instructions must include setDestinationObject({expected_destination})."
        )
    elif destination_objects != [expected_destination]:
        issues.append(
            "instructions must not invent destination objects; "
            f"use only setDestinationObject({expected_destination})."
        )

    expected_sector = f"set({mission.dam_column},{mission.dam_row})"
    if expected_sector not in plan.instructions:
        issues.append(f"instructions must include target sector {expected_sector}.")

    required_instructions = ["set(destroy)", "set(return)", "flyToLocation"]
    for required_instruction in required_instructions:
        if required_instruction not in plan.instructions:
            issues.append(f"instructions must include {required_instruction}.")

    return issues


# Convert validation output into a JSON-safe log payload.
def validation_for_log(result: ValidationResult) -> dict[str, object]:
    return {"passed": result.passed, "issues": result.issues}
