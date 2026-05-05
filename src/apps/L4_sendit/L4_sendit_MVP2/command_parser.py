# AI command parser for the L4 sendit MVP2 Stage 1 boundary.

import json
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from src.apps.L4_sendit.L4_sendit_MVP1.models import ShipmentCommand
from src.apps.L4_sendit.L4_sendit_MVP2.config import ModelConfig
from src.apps.L4_sendit.L4_sendit_MVP2.models import CommandParseResult, ParsedCommand
from src.apps.L4_sendit.L4_sendit_MVP2.validator import validate_parsed_command


COMMAND_PARSER_INSTRUCTIONS = """\
You parse one operational shipment command into validated shipment fields.
Return only the requested structured data.
Normalize weights to integer kilograms and budget to integer PP.
Preserve Polish wording exactly, including mojibake-like characters if present.
Use special_notes = "none" when the command says there are no special notes.
Do not infer route codes, categories, fees, wagons, or declaration text.
If a required command field is missing, list it in missing_fields and lower confidence.
"""


# Parse a command with a real model call guarded by max_model_requests.
def parse_command_with_ai(command_text: str, model_config: ModelConfig) -> CommandParseResult:
    guard = _ModelRequestGuard(model_config.max_model_requests)
    guard.reserve_request()

    client = OpenAI(api_key=model_config.api_key)
    response = client.responses.parse(
        model=model_config.command_parse_model,
        instructions=COMMAND_PARSER_INSTRUCTIONS,
        input=_build_command_parser_input(command_text),
        text_format=ParsedCommand,
        max_output_tokens=700,
    )

    parsed_command = response.output_parsed
    if parsed_command is None:
        raise ValueError("AI command parser returned no parsed structured output.")

    return _build_result(parsed_command, response.model_dump(mode="json"))


# Parse a command from a saved model-shaped JSON payload for local validation.
def parse_command_from_mock(command_text: str, raw_model_response: dict[str, Any]) -> CommandParseResult:
    _ = command_text
    raw_payload = _extract_mock_payload(raw_model_response)

    try:
        parsed_command = ParsedCommand.model_validate(raw_payload)
    except ValidationError as exc:
        raise ValueError(f"Mock command parser output failed schema validation: {exc}") from exc

    return _build_result(parsed_command, raw_model_response)


# Load a model-shaped JSON payload from disk.
def load_mock_model_response(raw_json_text: str) -> dict[str, Any]:
    try:
        raw_model_response = json.loads(raw_json_text.lstrip("\ufeff"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Mock model response is not valid JSON: {exc}") from exc

    if not isinstance(raw_model_response, dict):
        raise ValueError("Mock model response must be a JSON object.")

    return raw_model_response


# Build the compact user input passed to the command parser model.
def _build_command_parser_input(command_text: str) -> str:
    return "\n".join(
        [
            "Parse this operational command.",
            "",
            "<command>",
            command_text.strip(),
            "</command>",
        ]
    )


# Build a validated parser result and MVP1-compatible command projection.
def _build_result(parsed_command: ParsedCommand, raw_model_response: dict[str, Any]) -> CommandParseResult:
    validation_results = validate_parsed_command(parsed_command)
    errors = [result.message for result in validation_results if result.status == "ERROR"]
    if errors:
        raise ValueError(f"AI command parser output failed validation: {', '.join(errors)}")

    shipment_command = ShipmentCommand(
        sender_identifier=parsed_command.sender_identifier,
        origin_point=parsed_command.origin_point,
        destination_point=parsed_command.destination_point,
        weight_kg=parsed_command.weight_kg,
        budget_pp=parsed_command.budget_pp,
        contents=parsed_command.contents,
        special_notes=parsed_command.special_notes,
    )

    return CommandParseResult(
        parsed_command=parsed_command,
        shipment_command=shipment_command,
        raw_model_response=raw_model_response,
    )


# Accept either a raw schema object or a wrapper with parsed_command.
def _extract_mock_payload(raw_model_response: dict[str, Any]) -> dict[str, Any]:
    payload = raw_model_response.get("parsed_command", raw_model_response)
    if not isinstance(payload, dict):
        raise ValueError("Mock model response payload must be a JSON object.")

    return payload


# Enforce the explicit Stage 1 model-call limit.
class _ModelRequestGuard:
    def __init__(self, max_requests: int) -> None:
        self._max_requests = max_requests
        self._used_requests = 0

    # Reserve one model request or fail before calling the provider.
    def reserve_request(self) -> None:
        if self._used_requests >= self._max_requests:
            raise ValueError("Model request guard reached DEFAULT_MAX_MODEL_REQUESTS.")

        self._used_requests += 1
