# This module defines the approved LLM boundary for Polish product interpretation.

from __future__ import annotations

import json
from typing import Any, Literal, Protocol, cast

from openai import OpenAI
from openai.types.shared.reasoning_effort import ReasoningEffort
from openai.types.shared_params.reasoning import Reasoning
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .config import LlmConfig
from .normalization import normalize_text


INTERPRETER_SCHEMA_NAME = "l14_polish_product_needs"

SYSTEM_PROMPT = """Interpret Polish product requests for a catalog search tool.
Return only structured product needs.
Do not choose catalog item codes, city codes, city names, availability, prices, or final answers.
Preserve numbers and units from the request. Normalize obvious unit phrases, for example "10 metrow" to value "10" and unit "m".
If a product is underspecified, mark missing details instead of guessing.
The caller will validate everything against a local CSV catalog."""


# Represent one normalized attribute extracted from a product phrase.
class ProductAttribute(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=40)
    value: str = Field(min_length=1, max_length=40)
    unit: str = Field(default="", max_length=20)


# Represent one product need returned by the interpreter.
class ProductNeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_request_fragment: str = Field(min_length=0, max_length=300)
    normalized_product_type: str = Field(min_length=1, max_length=80)
    aliases: list[str] = Field(default_factory=list, max_length=8)
    attributes: list[ProductAttribute] = Field(default_factory=list, max_length=12)
    required_terms: list[str] = Field(default_factory=list, max_length=12)
    optional_terms: list[str] = Field(default_factory=list, max_length=12)
    missing_details: list[str] = Field(default_factory=list, max_length=8)
    confidence: Literal["high", "medium", "low"]

    # Require at least one searchable product identity signal.
    @field_validator("required_terms")
    @classmethod
    def validate_required_terms(cls, value: list[str]) -> list[str]:
        return [term.strip() for term in value if term.strip()]


# Represent the full structured interpreter response.
class QueryInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ProductNeed] = Field(min_length=1, max_length=3)
    needs_clarification: bool
    clarification_reason: str = Field(default="", max_length=300)

    # Keep clarification payloads explicit enough for deterministic recovery.
    @field_validator("clarification_reason")
    @classmethod
    def validate_clarification_reason(cls, value: str) -> str:
        return value.strip()


# Define the minimum client protocol needed for fake and real OpenAI clients.
class ResponsesClient(Protocol):
    def create(self, **kwargs: Any) -> Any:
        ...


# Build the typed reasoning configuration expected by the OpenAI SDK.
def build_reasoning_config(config: LlmConfig) -> Reasoning:
    return {"effort": cast(ReasoningEffort, config.reasoning_effort)}


# Build the strict structured-output format for the interpreter call.
def normalize_openai_json_schema(node: Any) -> Any:
    if isinstance(node, dict):
        normalized = {
            key: normalize_openai_json_schema(value)
            for key, value in node.items()
            if key != "default"
        }
        properties = normalized.get("properties")
        if isinstance(properties, dict):
            normalized["required"] = list(properties.keys())
            normalized["additionalProperties"] = False
        return normalized
    if isinstance(node, list):
        return [normalize_openai_json_schema(item) for item in node]
    return node


# Build the strict structured-output format for the interpreter call.
def build_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "name": INTERPRETER_SCHEMA_NAME,
        "schema": normalize_openai_json_schema(QueryInterpretation.model_json_schema()),
        "strict": True,
    }


# Extract text output from the OpenAI response object or a simple fake.
def extract_response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        return output_text
    if isinstance(response, dict) and isinstance(response.get("output_text"), str):
        return response["output_text"]
    raise ValueError("Interpreter response does not contain output_text.")


# Parse and validate one structured interpreter payload.
def parse_interpreter_output(output_text: str) -> QueryInterpretation:
    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError as error:
        raise ValueError("Interpreter output must be valid JSON.") from error

    try:
        return QueryInterpretation.model_validate(payload)
    except ValidationError as error:
        raise ValueError("Interpreter output does not match the schema.") from error


# Return a stable cache key for repeated exact params values.
def build_cache_key(params: str) -> str:
    return normalize_text(params)


# Interpret Polish params text through the approved no-tool model call.
class QueryInterpreter:
    # Keep one process-local cache so repeated agent retries do not spend twice.
    def __init__(self, config: LlmConfig, client: Any | None = None) -> None:
        self.config = config
        self.client = client or OpenAI(api_key=config.api_key)
        self.cache: dict[str, QueryInterpretation] = {}

    # Convert Polish free-form params into structured product needs.
    def interpret(self, params: str) -> QueryInterpretation:
        trimmed_params = params.strip()
        if not trimmed_params:
            return QueryInterpretation(
                items=[
                    ProductNeed(
                        raw_request_fragment="",
                        normalized_product_type="unknown",
                        confidence="low",
                        missing_details=["product description"],
                    )
                ],
                needs_clarification=True,
                clarification_reason="Brak opisu produktu.",
            )
        if len(trimmed_params) > self.config.max_input_chars:
            raise ValueError(
                f"params cannot be longer than {self.config.max_input_chars} characters."
            )

        cache_key = build_cache_key(trimmed_params)
        if cache_key in self.cache:
            return self.cache[cache_key]

        last_error: Exception | None = None
        for _attempt in range(self.config.retry_limit + 1):
            try:
                interpretation = self.call_model(trimmed_params)
                self.cache[cache_key] = interpretation
                return interpretation
            except ValueError as error:
                last_error = error

        raise ValueError("Interpreter failed to return valid structured output.") from last_error

    # Make one Responses API call and parse the strict output.
    def call_model(self, params: str) -> QueryInterpretation:
        response = self.client.responses.create(
            model=self.config.model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": params},
            ],
            reasoning=build_reasoning_config(self.config),
            max_output_tokens=self.config.max_output_tokens,
            text={"format": build_response_format()},
        )
        return parse_interpreter_output(extract_response_text(response))
