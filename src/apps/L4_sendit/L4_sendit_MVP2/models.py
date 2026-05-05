# Data structures for the L4 sendit MVP2 AI-assisted workflow.

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from src.apps.L4_sendit.L4_sendit_MVP1.models import ShipmentCommand


# Represent validated command fields returned by the AI command parser.
class ParsedCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sender_identifier: str = Field(min_length=1)
    origin_point: str = Field(min_length=1)
    destination_point: str = Field(min_length=1)
    weight_kg: int = Field(gt=0)
    budget_pp: int = Field(ge=0)
    contents: str = Field(min_length=1)
    special_notes: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    missing_fields: list[str]
    uncertainty_notes: list[str]


@dataclass(frozen=True)
# Store the parsed command plus the MVP1-compatible command projection.
class CommandParseResult:
    parsed_command: ParsedCommand
    shipment_command: ShipmentCommand
    raw_model_response: dict


@dataclass(frozen=True)
# Store one deterministic validation result for the MVP2 Stage 1 boundary.
class CommandValidationResult:
    status: str
    message: str
