# AI-backed Stage 4 evidence extraction for the L4 sendit MVP2 workflow.

import base64
import hashlib
import json
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from openai import OpenAI
from pydantic import ValidationError

from src.apps.L4_sendit.L4_sendit_MVP2.config import ModelConfig
from src.apps.L4_sendit.L4_sendit_MVP2.models import (
    EvidenceContext,
    EvidenceContextSource,
    EvidenceExtractionResult,
    EvidencePackage,
    SelectedSource,
    SelectedSources,
    SupportedTaskDefinition,
    TaskUnderstanding,
)
from src.apps.L4_sendit.L4_sendit_MVP2.validator import (
    raise_if_evidence_package_invalid,
    validate_evidence_package,
)


EVIDENCE_EXTRACTION_INSTRUCTIONS = """\
You extract only explicit evidence-backed facts from the provided selected sources.
Use only the attached source contents and images.
Do not invent facts, final task answers, or unsupported domain conclusions.
For markdown facts, copy a short exact evidence_quote from the source text.
For image facts, use evidence_kind image_region or image_description and provide an inspectable evidence_locator.
If a required fact target is not supported by the provided sources, add it to missing_facts instead of guessing.
Return only JSON matching the requested schema.
"""


@dataclass(frozen=True)
# Store one selected source with resolved local content for Stage 4.
class _LoadedSource:
    path: str
    source_type: str
    documentation_need: str
    absolute_path: Path
    size_bytes: int
    sha256: str
    text_content: str | None
    image_bytes: bytes | None


# === KNOWN_TASK: spk_transport_declaration ===================================
# These fact targets define what the current supported task needs from Stage 4.
# Add new task-specific target builders when future known tasks gain executors.
# =============================================================================
KNOWN_TASK_FACT_TARGETS: dict[str, dict[str, tuple[str, ...]]] = {
    "spk_transport_declaration": {
        "declaration format": ("declaration_template_fields",),
        "route availability and route code": ("route_code", "route_status"),
        "category rules": ("disabled_route_exception",),
        "payment rules": ("system_funded_categories",),
        "wagon allocation rules": ("standard_capacity_kg", "additional_wagon_capacity_kg"),
    }
}


# Extract validated evidence from the currently selected sources.
def extract_evidence_with_ai(
    task_understanding: TaskUnderstanding,
    selected_sources: SelectedSources,
    repo_root: Path,
    model_config: ModelConfig,
    supported_tasks: dict[str, SupportedTaskDefinition],
) -> tuple[EvidenceExtractionResult, str]:
    loaded_sources = _load_selected_sources(repo_root, selected_sources.selected_sources)
    evidence_context = _build_evidence_context(task_understanding, loaded_sources)
    model_name, response = _run_model_extraction(
        task_understanding=task_understanding,
        loaded_sources=loaded_sources,
        evidence_context=evidence_context,
        model_config=model_config,
    )

    raw_payload = json.loads(response.output_text)
    evidence_package = EvidencePackage.model_validate(raw_payload)
    result = _build_result(
        evidence_package=evidence_package,
        evidence_context=evidence_context,
        raw_model_response=response.model_dump(mode="json"),
        task_understanding=task_understanding,
        selected_sources=selected_sources,
        loaded_sources=loaded_sources,
        supported_tasks=supported_tasks,
    )
    return result, model_name


# Extract validated evidence from a saved model-shaped JSON payload.
def extract_evidence_from_mock(
    raw_model_response: dict[str, Any],
    task_understanding: TaskUnderstanding,
    selected_sources: SelectedSources,
    repo_root: Path,
    supported_tasks: dict[str, SupportedTaskDefinition],
) -> EvidenceExtractionResult:
    loaded_sources = _load_selected_sources(repo_root, selected_sources.selected_sources)
    evidence_context = _build_evidence_context(task_understanding, loaded_sources)
    raw_payload = _extract_mock_payload(raw_model_response)

    try:
        evidence_package = EvidencePackage.model_validate(raw_payload)
    except ValidationError as exc:
        raise ValueError(f"Mock evidence extraction output failed schema validation: {exc}") from exc

    return _build_result(
        evidence_package=evidence_package,
        evidence_context=evidence_context,
        raw_model_response=raw_model_response,
        task_understanding=task_understanding,
        selected_sources=selected_sources,
        loaded_sources=loaded_sources,
        supported_tasks=supported_tasks,
    )


# Load a model-shaped evidence extraction JSON payload from disk.
def load_mock_evidence_response(raw_json_text: str) -> dict[str, Any]:
    try:
        raw_model_response = json.loads(raw_json_text.lstrip("\ufeff"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Mock evidence extraction response is not valid JSON: {exc}") from exc

    if not isinstance(raw_model_response, dict):
        raise ValueError("Mock evidence extraction response must be a JSON object.")

    return raw_model_response


# Load the content of selected sources under the repository root.
def _load_selected_sources(repo_root: Path, selected_sources: list[SelectedSource]) -> list[_LoadedSource]:
    repo_root = repo_root.resolve()
    loaded_sources: list[_LoadedSource] = []

    for selected_source in selected_sources:
        absolute_path = (repo_root / selected_source.path).resolve()
        raw_bytes = absolute_path.read_bytes()

        text_content: str | None = None
        image_bytes: bytes | None = None
        if selected_source.source_type == "markdown":
            text_content = raw_bytes.decode("utf-8")
        elif selected_source.source_type == "image":
            image_bytes = raw_bytes

        loaded_sources.append(
            _LoadedSource(
                path=selected_source.path,
                source_type=selected_source.source_type,
                documentation_need=selected_source.documentation_need,
                absolute_path=absolute_path,
                size_bytes=len(raw_bytes),
                sha256=hashlib.sha256(raw_bytes).hexdigest(),
                text_content=text_content,
                image_bytes=image_bytes,
            )
        )

    return loaded_sources


# Build the deterministic evidence context artifact for this extraction step.
def _build_evidence_context(
    task_understanding: TaskUnderstanding,
    loaded_sources: list[_LoadedSource],
) -> EvidenceContext:
    required_fact_targets = _build_required_fact_targets(task_understanding, loaded_sources)
    context_sources = [
        EvidenceContextSource(
            path=loaded_source.path,
            source_type=loaded_source.source_type,
            documentation_need=loaded_source.documentation_need,
            sha256=loaded_source.sha256,
            size_bytes=loaded_source.size_bytes,
            text_char_count=len(loaded_source.text_content) if loaded_source.text_content is not None else None,
        )
        for loaded_source in loaded_sources
    ]

    return EvidenceContext(
        task_name=task_understanding.task_name,
        selected_source_count=len(loaded_sources),
        required_fact_targets=required_fact_targets,
        sources=context_sources,
    )


# Build the required fact targets for the current supported task and source scope.
def _build_required_fact_targets(
    task_understanding: TaskUnderstanding,
    loaded_sources: list[_LoadedSource],
) -> list[str]:
    task_target_map = KNOWN_TASK_FACT_TARGETS.get(task_understanding.task_name, {})
    required_targets: list[str] = []

    for loaded_source in loaded_sources:
        required_targets.extend(task_target_map.get(loaded_source.documentation_need, ()))

    return list(dict.fromkeys(required_targets))


# Run one extraction call with the text or vision model depending on selected sources.
def _run_model_extraction(
    task_understanding: TaskUnderstanding,
    loaded_sources: list[_LoadedSource],
    evidence_context: EvidenceContext,
    model_config: ModelConfig,
):
    client = OpenAI(api_key=model_config.api_key)
    has_images = any(loaded_source.source_type == "image" for loaded_source in loaded_sources)
    if has_images:
        model_name = model_config.vision_extraction_model
        response = client.responses.create(
            model=model_name,
            instructions=EVIDENCE_EXTRACTION_INSTRUCTIONS,
            input=cast(Any, _build_vision_input(task_understanding, loaded_sources, evidence_context)),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "evidence_package",
                    "schema": EvidencePackage.model_json_schema(),
                    "strict": True,
                }
            },
        )
        return model_name, response

    model_name = model_config.text_extraction_model
    response = client.responses.create(
        model=model_name,
        instructions=EVIDENCE_EXTRACTION_INSTRUCTIONS,
        input=_build_text_input(task_understanding, loaded_sources, evidence_context),
        text={
            "format": {
                "type": "json_schema",
                "name": "evidence_package",
                "schema": EvidencePackage.model_json_schema(),
                "strict": True,
            }
        },
    )
    return model_name, response


# Build the text-only evidence extraction input.
def _build_text_input(
    task_understanding: TaskUnderstanding,
    loaded_sources: list[_LoadedSource],
    evidence_context: EvidenceContext,
) -> str:
    context = {
        "task_understanding": task_understanding.model_dump(mode="json"),
        "required_fact_targets": evidence_context.required_fact_targets,
        "markdown_sources": [
            {
                "path": loaded_source.path,
                "documentation_need": loaded_source.documentation_need,
                "content": loaded_source.text_content,
            }
            for loaded_source in loaded_sources
            if loaded_source.text_content is not None
        ],
    }

    return "\n".join(
        [
            "Extract only explicit evidence-backed facts from the provided markdown sources.",
            "Use missing_facts when a required fact target is not explicitly supported.",
            "",
            json.dumps(context, ensure_ascii=False, indent=2),
        ]
    )


# Build the multimodal evidence extraction input when images are selected.
def _build_vision_input(
    task_understanding: TaskUnderstanding,
    loaded_sources: list[_LoadedSource],
    evidence_context: EvidenceContext,
) -> list[dict[str, object]]:
    markdown_sources = [
        {
            "path": loaded_source.path,
            "documentation_need": loaded_source.documentation_need,
            "content": loaded_source.text_content,
        }
        for loaded_source in loaded_sources
        if loaded_source.text_content is not None
    ]
    image_sources = [
        loaded_source
        for loaded_source in loaded_sources
        if loaded_source.image_bytes is not None
    ]
    context = {
        "task_understanding": task_understanding.model_dump(mode="json"),
        "required_fact_targets": evidence_context.required_fact_targets,
        "markdown_sources": markdown_sources,
        "image_sources": [
            {
                "path": loaded_source.path,
                "documentation_need": loaded_source.documentation_need,
            }
            for loaded_source in image_sources
        ],
    }
    content: list[dict[str, str]] = [
        {
            "type": "input_text",
            "text": "\n".join(
                [
                    "Extract only explicit evidence-backed facts from the provided markdown sources and attached images.",
                    "Use the attached images for image facts only.",
                    "",
                    json.dumps(context, ensure_ascii=False, indent=2),
                ]
            ),
        }
    ]

    for loaded_source in image_sources:
        image_bytes = loaded_source.image_bytes
        if image_bytes is None:
            continue

        content.append(
            {
                "type": "input_text",
                "text": (
                    f"Attached image source path: {loaded_source.path}\n"
                    f"Documentation need: {loaded_source.documentation_need}"
                ),
            }
        )
        content.append(
            {
                "type": "input_image",
                "image_url": _to_data_url(loaded_source.absolute_path, image_bytes),
            }
        )

    return [{"role": "user", "content": content}]


# Convert one local image file into a data URL accepted by the Responses API.
def _to_data_url(image_path: Path, image_bytes: bytes) -> str:
    mime_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    encoded_bytes = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded_bytes}"


# Build a validated Stage 4 result.
def _build_result(
    evidence_package: EvidencePackage,
    evidence_context: EvidenceContext,
    raw_model_response: dict[str, Any],
    task_understanding: TaskUnderstanding,
    selected_sources: SelectedSources,
    loaded_sources: list[_LoadedSource],
    supported_tasks: dict[str, SupportedTaskDefinition],
) -> EvidenceExtractionResult:
    markdown_source_texts = {
        loaded_source.path: loaded_source.text_content
        for loaded_source in loaded_sources
        if loaded_source.text_content is not None
    }
    validation_results = validate_evidence_package(
        evidence_package=evidence_package,
        evidence_context=evidence_context,
        task_understanding=task_understanding,
        selected_sources=selected_sources,
        markdown_source_texts=markdown_source_texts,
        supported_tasks=supported_tasks,
    )
    raise_if_evidence_package_invalid(validation_results)

    return EvidenceExtractionResult(
        evidence_package=evidence_package,
        raw_model_response=raw_model_response,
        evidence_context=evidence_context,
    )


# Accept either a raw schema object or a wrapper with evidence_package.
def _extract_mock_payload(raw_model_response: dict[str, Any]) -> dict[str, Any]:
    payload = raw_model_response.get("evidence_package", raw_model_response)
    if isinstance(payload, dict) and "output" in payload:
        payload = _extract_openai_output_text_payload(payload)
    if not isinstance(payload, dict):
        raise ValueError("Mock evidence extraction response payload must be a JSON object.")

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
