# Data structures for the L4 sendit MVP2 Stage 1-4 workflow.

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# Represent the provided inputs for the currently supported known task.
class KnownTaskProvidedInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # === KNOWN_TASK: spk_transport_declaration ===============================
    # These explicit fields describe the only currently supported task input
    # shape. Add new task-specific input models when new known tasks are added.
    # =========================================================================
    sender_identifier: str = Field(min_length=1)
    origin_point: str = Field(min_length=1)
    destination_point: str = Field(min_length=1)
    weight_kg: int = Field(gt=0)
    budget_pp: int = Field(ge=0)
    contents: str = Field(min_length=1)
    special_notes: str = Field(min_length=1)


# Represent one documentation need identified from the command.
class DocumentationNeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    need: str = Field(min_length=1)
    reason: str = Field(min_length=1)


# Represent the validated Stage 1 task understanding produced by the model.
class TaskUnderstanding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_name: str = Field(min_length=1)
    task_goal: str = Field(min_length=1)
    expected_output_kind: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    provided_inputs: KnownTaskProvidedInputs
    documentation_needs: list[DocumentationNeed]
    success_criteria: list[str]
    missing_inputs: list[str]
    uncertainty_notes: list[str]
    confidence: float = Field(ge=0.0, le=1.0)


@dataclass(frozen=True)
# Store one supported task definition known to deterministic code.
class SupportedTaskDefinition:
    task_name: str
    task_goal: str
    expected_output_kind: str
    result_kind: str
    domain: str
    required_input_fields: tuple[str, ...]
    documentation_need_names: tuple[str, ...]


@dataclass(frozen=True)
# Store the validated Stage 1 result plus the raw provider payload.
class TaskUnderstandingResult:
    task_understanding: TaskUnderstanding
    raw_model_response: dict[str, Any]


@dataclass(frozen=True)
# Store one deterministic validation result for the Stage 1 boundary.
class ValidationResult:
    status: str
    message: str


# Represent one local reference file available for later source selection.
class ReferenceInventoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    source_type: str = Field(pattern="^(markdown|image|other)$")
    size_bytes: int = Field(ge=0)
    hint: str = Field(min_length=1)


# Represent one source selected for downstream evidence extraction.
class SelectedSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    source_type: str = Field(pattern="^(markdown|image|other)$")
    documentation_need: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    intended_use: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


# Represent one inventory source explicitly rejected during selection.
class RejectedSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    reason: str = Field(min_length=1)


# Represent the validated Stage 3 source selection package.
class SelectedSources(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected_sources: list[SelectedSource]
    rejected_sources: list[RejectedSource]
    missing_sources: list[str]
    uncertainty_notes: list[str]


@dataclass(frozen=True)
# Store the validated Stage 3 result plus the raw provider payload.
class SourceSelectionResult:
    selected_sources: SelectedSources
    raw_model_response: dict[str, Any]


# Represent one validated evidence fact extracted from selected sources.
class EvidenceFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    value: str | int | list[str]
    source_path: str = Field(min_length=1)
    source_type: str = Field(pattern="^(markdown|image|other)$")
    evidence_kind: str = Field(pattern="^(text_quote|image_region|image_description)$")
    evidence_note: str = Field(min_length=1)
    evidence_quote: str | None
    evidence_locator: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty_notes: list[str]


# Represent coverage notes for one selected source during extraction.
class SourceCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    used: bool
    notes: str = Field(min_length=1)


# Represent the validated Stage 4 evidence package.
class EvidencePackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facts: list[EvidenceFact]
    missing_facts: list[str]
    conflicts: list[str]
    source_coverage: list[SourceCoverage]


# Represent one selected source inside the deterministic evidence context artifact.
class EvidenceContextSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    source_type: str = Field(pattern="^(markdown|image|other)$")
    documentation_need: str = Field(min_length=1)
    sha256: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    text_char_count: int | None = Field(default=None, ge=0)


# Represent the deterministic extraction scope and content hashes.
class EvidenceContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_name: str = Field(min_length=1)
    selected_source_count: int = Field(ge=0)
    required_fact_targets: list[str]
    sources: list[EvidenceContextSource]


@dataclass(frozen=True)
# Store the validated Stage 4 result plus raw provider payloads and context.
class EvidenceExtractionResult:
    evidence_package: EvidencePackage
    raw_model_response: dict[str, Any]
    evidence_context: EvidenceContext


# Represent one link from a result field back to an evidence fact.
class EvidenceLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_field: str = Field(min_length=1)
    fact_name: str = Field(min_length=1)


# Represent the known declaration data produced for the supported task.
class DeclarationTaskResultData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # === KNOWN_TASK: spk_transport_declaration ===============================
    # These fields describe the only currently supported task result shape.
    # Add new task-specific result models when new known tasks are implemented.
    # =========================================================================
    sender_identifier: str = Field(min_length=1)
    origin_point: str = Field(min_length=1)
    destination_point: str = Field(min_length=1)
    route_code: str = Field(min_length=1)
    category: str = Field(min_length=1)
    contents: str = Field(min_length=1)
    declared_weight_kg: int = Field(gt=0)
    wdp: int = Field(ge=0)
    special_notes: str = Field(min_length=1)
    amount_due_pp: int = Field(ge=0)


# Represent the validated Stage 5 task result.
class TaskResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_name: str = Field(min_length=1)
    result_kind: str = Field(min_length=1)
    result: DeclarationTaskResultData
    evidence_links: list[EvidenceLink]
    uncertainty_notes: list[str]


@dataclass(frozen=True)
# Store the validated Stage 5 result plus an optional raw provider payload.
class TaskExecutionResult:
    task_result: TaskResult
    raw_model_response: dict[str, Any]
