# AI source selector for the L4 sendit MVP2 Stage 2 boundary.

import json
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from src.apps.L4_sendit.L4_sendit_MVP2.config import ModelConfig
from src.apps.L4_sendit.L4_sendit_MVP2.models import (
    ParsedCommand,
    ReferenceInventoryItem,
    SelectedSources,
    SourceSelectionResult,
)
from src.apps.L4_sendit.L4_sendit_MVP2.validator import (
    raise_if_source_selection_invalid,
    validate_selected_sources,
)


SOURCE_SELECTOR_INSTRUCTIONS = """\
You select local SPK reference files for later extraction stages.
Choose only paths from the provided inventory.
Do not extract facts from the references.
Do not infer route codes, category, payment, wagons, WDP, or declaration text.
Return missing or uncertain source needs explicitly.
Return only the requested structured data.
"""


# Select local reference sources with a real model call guarded by max_model_requests.
def select_sources_with_ai(
    parsed_command: ParsedCommand,
    inventory: list[ReferenceInventoryItem],
    model_config: ModelConfig,
) -> SourceSelectionResult:
    guard = _ModelRequestGuard(model_config.max_model_requests)
    guard.reserve_request()

    client = OpenAI(api_key=model_config.api_key)
    response = client.responses.parse(
        model=model_config.source_selection_model,
        instructions=SOURCE_SELECTOR_INSTRUCTIONS,
        input=_build_source_selector_input(parsed_command, inventory),
        text_format=SelectedSources,
        max_output_tokens=1200,
    )

    selected_sources = response.output_parsed
    if selected_sources is None:
        raise ValueError("AI source selector returned no parsed structured output.")

    return _build_result(selected_sources, inventory, response.model_dump(mode="json"))


# Select local reference sources from saved model-shaped JSON for local validation.
def select_sources_from_mock(
    raw_model_response: dict[str, Any],
    inventory: list[ReferenceInventoryItem],
) -> SourceSelectionResult:
    raw_payload = _extract_mock_payload(raw_model_response)

    try:
        selected_sources = SelectedSources.model_validate(raw_payload)
    except ValidationError as exc:
        raise ValueError(f"Mock source selector output failed schema validation: {exc}") from exc

    return _build_result(selected_sources, inventory, raw_model_response)


# Load a model-shaped source selection JSON payload from disk.
def load_mock_source_selection_response(raw_json_text: str) -> dict[str, Any]:
    try:
        raw_model_response = json.loads(raw_json_text.lstrip("\ufeff"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Mock source selection response is not valid JSON: {exc}") from exc

    if not isinstance(raw_model_response, dict):
        raise ValueError("Mock source selection response must be a JSON object.")

    return raw_model_response


# Build compact source selection input without full reference contents.
def _build_source_selector_input(
    parsed_command: ParsedCommand,
    inventory: list[ReferenceInventoryItem],
) -> str:
    context = {
        "parsed_command_summary": {
            "sender_identifier": parsed_command.sender_identifier,
            "origin_point": parsed_command.origin_point,
            "destination_point": parsed_command.destination_point,
            "weight_kg": parsed_command.weight_kg,
            "budget_pp": parsed_command.budget_pp,
            "contents": parsed_command.contents,
            "special_notes": parsed_command.special_notes,
        },
        "reference_inventory": [item.model_dump(mode="json") for item in inventory],
        "required_source_categories": [
            "declaration template",
            "broad SPK rules",
            "disabled route evidence",
            "wagon capacity",
            "WDP meaning",
        ],
    }

    return "\n".join(
        [
            "Select local SPK reference files for later extraction stages.",
            "Use only paths from this JSON context.",
            "",
            json.dumps(context, ensure_ascii=False, indent=2),
        ]
    )


# Build a validated source selection result.
def _build_result(
    selected_sources: SelectedSources,
    inventory: list[ReferenceInventoryItem],
    raw_model_response: dict[str, Any],
) -> SourceSelectionResult:
    validation_results = validate_selected_sources(selected_sources, inventory)
    raise_if_source_selection_invalid(validation_results)

    return SourceSelectionResult(
        selected_sources=selected_sources,
        raw_model_response=raw_model_response,
    )


# Accept either a raw schema object or a wrapper with selected_sources_result.
def _extract_mock_payload(raw_model_response: dict[str, Any]) -> dict[str, Any]:
    payload = raw_model_response.get("selected_sources_result", raw_model_response)
    if not isinstance(payload, dict):
        raise ValueError("Mock source selection response payload must be a JSON object.")

    return payload


# Enforce the explicit Stage 2 model-call limit.
class _ModelRequestGuard:
    # Initialize the local model-request counter for one selector step.
    def __init__(self, max_requests: int) -> None:
        self._max_requests = max_requests
        self._used_requests = 0

    # Reserve one model request or fail before calling the provider.
    def reserve_request(self) -> None:
        if self._used_requests >= self._max_requests:
            raise ValueError("Model request guard reached DEFAULT_MAX_MODEL_REQUESTS.")

        self._used_requests += 1
