# AI-backed Stage 1 task understanding for the L4 sendit MVP2 workflow.

import json
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from src.apps.L4_sendit.L4_sendit_MVP2.config import ModelConfig
from src.apps.L4_sendit.L4_sendit_MVP2.models import (
    SupportedTaskDefinition,
    TaskUnderstanding,
    TaskUnderstandingResult,
)
from src.apps.L4_sendit.L4_sendit_MVP2.task_registry import build_supported_task_prompt_summary
from src.apps.L4_sendit.L4_sendit_MVP2.validator import (
    raise_if_task_understanding_invalid,
    validate_task_understanding,
)


TASK_UNDERSTANDING_INSTRUCTIONS = """\
You identify which supported task the operational command requests.
Choose only from the provided supported task list.
Return structured task understanding with provided inputs, documentation needs, success criteria, missing inputs, and uncertainty notes.
Do not invent unsupported task types, fallback executors, or final task results.
Return only JSON matching the requested schema.
"""


# Understand one command with a real model call guarded by max_model_requests.
def understand_task_with_ai(
    command_text: str,
    model_config: ModelConfig,
    supported_tasks: dict[str, SupportedTaskDefinition],
) -> TaskUnderstandingResult:
    guard = _ModelRequestGuard(model_config.max_model_requests)
    guard.reserve_request()

    client = OpenAI(api_key=model_config.api_key)
    response = client.responses.create(
        model=model_config.command_parse_model,
        instructions=TASK_UNDERSTANDING_INSTRUCTIONS,
        input=_build_task_understanding_input(command_text),
        text={
            "format": {
                "type": "json_schema",
                "name": "task_understanding",
                "schema": TaskUnderstanding.model_json_schema(),
                "strict": True,
            }
        },
    )

    raw_payload = json.loads(response.output_text)
    task_understanding = TaskUnderstanding.model_validate(raw_payload)
    return _build_result(task_understanding, supported_tasks, response.model_dump(mode="json"))


# Understand one command from a saved model-shaped JSON payload.
def understand_task_from_mock(
    raw_model_response: dict[str, Any],
    supported_tasks: dict[str, SupportedTaskDefinition],
) -> TaskUnderstandingResult:
    raw_payload = _extract_mock_payload(raw_model_response)

    try:
        task_understanding = TaskUnderstanding.model_validate(raw_payload)
    except ValidationError as exc:
        raise ValueError(f"Mock task understanding output failed schema validation: {exc}") from exc

    return _build_result(task_understanding, supported_tasks, raw_model_response)


# Load a model-shaped task understanding JSON payload from disk.
def load_mock_task_understanding_response(raw_json_text: str) -> dict[str, Any]:
    try:
        raw_model_response = json.loads(raw_json_text.lstrip("\ufeff"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Mock task understanding response is not valid JSON: {exc}") from exc

    if not isinstance(raw_model_response, dict):
        raise ValueError("Mock task understanding response must be a JSON object.")

    return raw_model_response


# Build the compact command-understanding input passed to the model.
def _build_task_understanding_input(command_text: str) -> str:
    context = {
        "supported_tasks": build_supported_task_prompt_summary(),
        "command_text": command_text.strip(),
    }

    return "\n".join(
        [
            "Identify the supported task requested by this command.",
            "Use only task_name values from the supported_tasks list.",
            "",
            json.dumps(context, ensure_ascii=False, indent=2),
        ]
    )


# Build a validated Stage 1 result.
def _build_result(
    task_understanding: TaskUnderstanding,
    supported_tasks: dict[str, SupportedTaskDefinition],
    raw_model_response: dict[str, Any],
) -> TaskUnderstandingResult:
    validation_results = validate_task_understanding(task_understanding, supported_tasks)
    raise_if_task_understanding_invalid(validation_results)

    return TaskUnderstandingResult(
        task_understanding=task_understanding,
        raw_model_response=raw_model_response,
    )


# Accept either a raw schema object or a wrapper with task_understanding.
def _extract_mock_payload(raw_model_response: dict[str, Any]) -> dict[str, Any]:
    payload = raw_model_response.get("task_understanding", raw_model_response)
    if not isinstance(payload, dict):
        raise ValueError("Mock task understanding response payload must be a JSON object.")

    return payload


# Enforce the explicit Stage 1 model-call limit.
class _ModelRequestGuard:
    # Initialize the local model-request counter for one Stage 1 run.
    def __init__(self, max_requests: int) -> None:
        self._max_requests = max_requests
        self._used_requests = 0

    # Reserve one model request or fail before calling the provider.
    def reserve_request(self) -> None:
        if self._used_requests >= self._max_requests:
            raise ValueError("Model request guard reached DEFAULT_MAX_MODEL_REQUESTS.")

        self._used_requests += 1
