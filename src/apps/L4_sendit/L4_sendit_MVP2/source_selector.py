# AI-backed Stage 3 source selection for the L4 sendit MVP2 workflow.

import json
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from src.apps.L4_sendit.L4_sendit_MVP2.config import ModelConfig
from src.apps.L4_sendit.L4_sendit_MVP2.models import (
    ReferenceInventoryItem,
    SelectedSources,
    SourceSelectionResult,
    SupportedTaskDefinition,
    TaskUnderstanding,
)
from src.apps.L4_sendit.L4_sendit_MVP2.validator import (
    raise_if_selected_sources_invalid,
    validate_selected_sources,
)


SOURCE_SELECTION_INSTRUCTIONS = """\
You select only the local reference files needed for the already identified task.
Choose only from the provided inventory paths.
Use documentation_need values exactly as they appear in task_understanding.documentation_needs.
Do not merge multiple documentation_need names into one string.
Do not invent paths, new files, final task answers, or extracted facts from document contents.
Preserve missing sources and uncertainty when the inventory is insufficient.
Return only JSON matching the requested schema.
"""


# Select Stage 3 sources with a real model call guarded by max_model_requests.
def select_sources_with_ai(
    task_understanding: TaskUnderstanding,
    reference_inventory: list[ReferenceInventoryItem],
    model_config: ModelConfig,
    supported_tasks: dict[str, SupportedTaskDefinition],
) -> SourceSelectionResult:
    guard = _ModelRequestGuard(model_config.max_model_requests)
    guard.reserve_request()

    client = OpenAI(api_key=model_config.api_key)
    response = client.responses.create(
        model=model_config.source_selection_model,
        instructions=SOURCE_SELECTION_INSTRUCTIONS,
        input=_build_source_selection_input(task_understanding, reference_inventory),
        text={
            "format": {
                "type": "json_schema",
                "name": "selected_sources",
                "schema": SelectedSources.model_json_schema(),
                "strict": True,
            }
        },
    )

    raw_payload = json.loads(response.output_text)
    selected_sources = SelectedSources.model_validate(raw_payload)
    return _build_result(
        selected_sources=selected_sources,
        task_understanding=task_understanding,
        reference_inventory=reference_inventory,
        supported_tasks=supported_tasks,
        raw_model_response=response.model_dump(mode="json"),
    )


# Select Stage 3 sources from a saved model-shaped JSON payload.
def select_sources_from_mock(
    raw_model_response: dict[str, Any],
    task_understanding: TaskUnderstanding,
    reference_inventory: list[ReferenceInventoryItem],
    supported_tasks: dict[str, SupportedTaskDefinition],
) -> SourceSelectionResult:
    raw_payload = _extract_mock_payload(raw_model_response)

    try:
        selected_sources = SelectedSources.model_validate(raw_payload)
    except ValidationError as exc:
        raise ValueError(f"Mock source selection output failed schema validation: {exc}") from exc

    return _build_result(
        selected_sources=selected_sources,
        task_understanding=task_understanding,
        reference_inventory=reference_inventory,
        supported_tasks=supported_tasks,
        raw_model_response=raw_model_response,
    )


# Load a model-shaped source selection JSON payload from disk.
def load_mock_source_selection_response(raw_json_text: str) -> dict[str, Any]:
    try:
        raw_model_response = json.loads(raw_json_text.lstrip("\ufeff"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Mock source selection response is not valid JSON: {exc}") from exc

    if not isinstance(raw_model_response, dict):
        raise ValueError("Mock source selection response must be a JSON object.")

    return raw_model_response


# Build the compact source-selection input passed to the model.
def _build_source_selection_input(
    task_understanding: TaskUnderstanding,
    reference_inventory: list[ReferenceInventoryItem],
) -> str:
    context = {
        "task_understanding": task_understanding.model_dump(mode="json"),
        "reference_inventory": [inventory_item.model_dump(mode="json") for inventory_item in reference_inventory],
    }

    return "\n".join(
        [
            "Choose the local reference files needed for this already identified task.",
            "Use only the exact inventory paths.",
            "For each selected source, documentation_need must exactly match one task_understanding.documentation_needs entry.",
            "Do not concatenate or rewrite documentation_need names.",
            "Do not extract facts from file contents in this step.",
            "",
            json.dumps(context, ensure_ascii=False, indent=2),
        ]
    )


# Build a validated Stage 3 result.
def _build_result(
    selected_sources: SelectedSources,
    task_understanding: TaskUnderstanding,
    reference_inventory: list[ReferenceInventoryItem],
    supported_tasks: dict[str, SupportedTaskDefinition],
    raw_model_response: dict[str, Any],
) -> SourceSelectionResult:
    validation_results = validate_selected_sources(
        selected_sources=selected_sources,
        task_understanding=task_understanding,
        reference_inventory=reference_inventory,
        supported_tasks=supported_tasks,
    )
    raise_if_selected_sources_invalid(validation_results)

    return SourceSelectionResult(
        selected_sources=selected_sources,
        raw_model_response=raw_model_response,
    )


# Accept either a raw schema object or a wrapper with selected_sources.
def _extract_mock_payload(raw_model_response: dict[str, Any]) -> dict[str, Any]:
    payload = raw_model_response.get("selected_sources", raw_model_response)
    if isinstance(payload, dict) and "output" in payload:
        payload = _extract_openai_output_text_payload(payload)
    if not isinstance(payload, dict):
        raise ValueError("Mock source selection response payload must be a JSON object.")

    return payload


# Extract the JSON payload from a saved OpenAI Responses API object.
def _extract_openai_output_text_payload(raw_response: dict[str, Any]) -> dict[str, Any]:
    output_items = raw_response.get("output", [])
    for output_item in output_items:
        for content_item in output_item.get("content", []):
            if content_item.get("type") != "output_text":
                continue

            text_payload = content_item.get("text", "")
            parsed_payload = json.loads(text_payload)
            if not isinstance(parsed_payload, dict):
                raise ValueError("OpenAI output_text payload must decode to a JSON object.")

            return parsed_payload

    raise ValueError("OpenAI response mock does not contain output_text JSON content.")


# Enforce the explicit Stage 3 model-call limit.
class _ModelRequestGuard:
    # Initialize the local model-request counter for one Stage 3 run.
    def __init__(self, max_requests: int) -> None:
        self._max_requests = max_requests
        self._used_requests = 0

    # Reserve one model request or fail before calling the provider.
    def reserve_request(self) -> None:
        if self._used_requests >= self._max_requests:
            raise ValueError("Model request guard reached DEFAULT_MAX_MODEL_REQUESTS.")

        self._used_requests += 1
