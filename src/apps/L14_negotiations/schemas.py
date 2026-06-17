# This module defines the public HTTP payload contract for the tool endpoint.

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


MIN_OUTPUT_BYTES = 4
MAX_OUTPUT_BYTES = 500
MAX_PARAMS_CHARS = 1_000


# Represent the only request shape accepted by the public tool endpoint.
class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    params: str = Field(min_length=1, max_length=MAX_PARAMS_CHARS)

    # Trim surrounding whitespace without accepting empty product descriptions.
    @field_validator("params")
    @classmethod
    def normalize_params(cls, value: str) -> str:
        trimmed_value = value.strip()
        if not trimmed_value:
            raise ValueError("params cannot be empty.")
        return trimmed_value


# Represent the response shape expected by the external course agent.
class ToolResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output: str

    # Enforce the byte budget from the task contract, not just character length.
    @field_validator("output")
    @classmethod
    def validate_output_size(cls, value: str) -> str:
        output_size = len(value.encode("utf-8"))
        if output_size < MIN_OUTPUT_BYTES:
            raise ValueError("output is too short.")
        if output_size > MAX_OUTPUT_BYTES:
            raise ValueError("output is too long.")
        return value


# Convert untrusted JSON into a typed request or raise one readable error.
def parse_tool_request(payload: dict[str, object]) -> ToolRequest:
    try:
        return ToolRequest.model_validate(payload)
    except ValidationError as error:
        raise ValueError("Request must contain only a non-empty string params field.") from error


# Convert a Polish answer string into the final JSON response payload.
def build_tool_response(output: str) -> dict[str, str]:
    response = ToolResponse(output=output)
    return response.model_dump()
