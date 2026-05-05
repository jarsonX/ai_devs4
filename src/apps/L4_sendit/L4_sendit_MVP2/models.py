# Data structures for the L4 sendit MVP2 AI-assisted workflow.

from dataclasses import dataclass
from typing import Literal

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


# Store the parsed command plus the MVP1-compatible command projection.
@dataclass(frozen=True)
class CommandParseResult:
    parsed_command: ParsedCommand
    shipment_command: ShipmentCommand
    raw_model_response: dict


# Store one deterministic validation result for the MVP2 Stage 1 boundary.
@dataclass(frozen=True)
class CommandValidationResult:
    status: str
    message: str


# Represent one local reference file available for source selection.
class ReferenceInventoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    source_type: Literal["markdown", "image", "other"]
    size_bytes: int = Field(ge=0)
    hint: str = Field(min_length=1)


# Represent one source selected by the AI source selector.
class SelectedSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    source_type: Literal["markdown", "image", "other"]
    reason: str = Field(min_length=1)
    intended_use: Literal[
        "text_fact_extraction",
        "image_fact_extraction",
        "template_reference",
        "supporting_context",
    ]
    confidence: float = Field(ge=0.0, le=1.0)


# Represent one source rejected by the AI source selector.
class RejectedSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    reason: str = Field(min_length=1)


# Represent validated source selection output returned by the model.
class SelectedSources(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected_sources: list[SelectedSource] = Field(min_length=1)
    rejected_sources: list[RejectedSource]
    missing_sources: list[str]
    uncertainty_notes: list[str]


# Store the selected sources plus the raw model response for inspection.
@dataclass(frozen=True)
class SourceSelectionResult:
    selected_sources: SelectedSources
    raw_model_response: dict
