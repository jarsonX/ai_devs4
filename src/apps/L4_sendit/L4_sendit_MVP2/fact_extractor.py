# AI-backed Stage 4 evidence extraction for the L4 sendit MVP2 workflow.

import base64
import hashlib
import json
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from openai import OpenAI
from pydantic import ValidationError

from src.apps.L4_sendit.L4_sendit_MVP2.config import ModelConfig
from src.apps.L4_sendit.L4_sendit_MVP2.models import (
    EvidenceContext,
    EvidenceContextSource,
    EvidenceFact,
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
When `shipment_category` is required, classify the shipment from `task_understanding.provided_inputs.contents`
against the provided category rules source and return only the category symbol such as `A`, `B`, `C`, `D`, `E`, or `X`.
Preserve confidence and uncertainty when the category mapping is interpretive rather than explicit.
When `resolved_terms` is required, return only task-relevant terminology entries in the form `TERM = expansion`.
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
        "declaration terminology": ("resolved_terms",),
        "route availability and route code": ("route_code", "route_status"),
        "category rules": ("shipment_category", "disabled_route_exception"),
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
            *_build_task_specific_extraction_guidance(evidence_context),
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
                    *_build_task_specific_extraction_guidance(evidence_context),
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


# Add narrow extraction guidance for task-specific fact targets.
def _build_task_specific_extraction_guidance(evidence_context: EvidenceContext) -> list[str]:
    guidance_lines: list[str] = []
    if "shipment_category" in evidence_context.required_fact_targets:
        guidance_lines.extend(
            [
                "For shipment_category, use the shipment contents from task_understanding.provided_inputs.contents.",
                "Ground the classification in the selected category rules source, not in route exceptions alone.",
                "Return the category symbol only in fact.value and explain uncertainty in uncertainty_notes when needed.",
            ]
        )
    if "resolved_terms" in evidence_context.required_fact_targets:
        guidance_lines.extend(
            [
                "For resolved_terms, include only abbreviations or glossary terms that are relevant to the current task output.",
                "Return resolved_terms as a list of strings formatted exactly like `TERM = expansion`.",
                "Do not dump the full glossary when only a subset is relevant to the current task.",
            ]
        )

    return guidance_lines


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
    _repair_markdown_evidence_quotes(evidence_package, markdown_source_texts)
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


# Repair markdown evidence quotes when the model returns a near-match instead of an exact substring.
def _repair_markdown_evidence_quotes(
    evidence_package: EvidencePackage,
    markdown_source_texts: dict[str, str],
) -> None:
    for fact in evidence_package.facts:
        if fact.source_type != "markdown" or fact.evidence_kind != "text_quote":
            continue

        source_text = markdown_source_texts.get(fact.source_path)
        if not source_text:
            continue
        if fact.evidence_quote and _normalize_for_quote_match(fact.evidence_quote) in _normalize_for_quote_match(source_text):
            continue

        repaired_quote = _find_best_quote_line(fact, source_text)
        if repaired_quote is not None:
            fact.evidence_quote = repaired_quote


# Find one source line that most likely matches the fact when the quote is slightly paraphrased.
def _find_best_quote_line(fact: EvidenceFact, source_text: str) -> str | None:
    raw_lines = source_text.splitlines()
    candidate_lines = [line for line in raw_lines if line.strip()]
    if not candidate_lines:
        return None

    query_tokens = _build_quote_repair_tokens(fact)
    if not query_tokens:
        return None

    scored_candidates: list[tuple[int, int, str]] = []
    for line_index, candidate_line in enumerate(raw_lines):
        if not candidate_line.strip():
            continue
        candidate_tokens = set(_tokenize_for_quote_repair(candidate_line))
        score = sum(1 for token in query_tokens if token in candidate_tokens)
        if score > 0:
            scored_candidates.append((line_index, score, candidate_line))

    if not scored_candidates:
        return None

    scored_candidates.sort(key=lambda item: item[1], reverse=True)
    best_index, best_score, best_line = scored_candidates[0]
    second_best_score = scored_candidates[1][1] if len(scored_candidates) > 1 else 0

    if best_score < 3:
        return None
    if best_score > second_best_score:
        return best_line.strip()

    repaired_span = _find_best_quote_span(raw_lines, scored_candidates, best_score)
    if repaired_span is not None:
        return repaired_span

    return raw_lines[best_index].strip()


# Join a short contiguous source span when one fact maps to several equally relevant lines.
def _find_best_quote_span(
    raw_lines: list[str],
    scored_candidates: list[tuple[int, int, str]],
    best_score: int,
) -> str | None:
    strong_indexes = [
        line_index
        for line_index, score, _candidate_line in scored_candidates
        if score >= max(2, best_score - 1)
    ]
    if not strong_indexes:
        return None

    grouped_indexes: list[list[int]] = []
    current_group: list[int] = [strong_indexes[0]]
    for line_index in strong_indexes[1:]:
        if line_index == current_group[-1] + 1:
            current_group.append(line_index)
            continue

        grouped_indexes.append(current_group)
        current_group = [line_index]
    grouped_indexes.append(current_group)

    scored_groups: list[tuple[int, int, int, int]] = []
    score_by_index = {line_index: score for line_index, score, _candidate_line in scored_candidates}
    for group in grouped_indexes:
        start_index = group[0]
        end_index = group[-1]
        group_score = sum(score_by_index.get(line_index, 0) for line_index in group)
        scored_groups.append((group_score, len(group), start_index, end_index))

    scored_groups.sort(key=lambda item: (item[0], -item[1], -item[2]), reverse=True)
    _group_score, group_length, start_index, end_index = scored_groups[0]
    if group_length <= 1:
        return None

    quote_lines = raw_lines[start_index : end_index + 1]
    return "\n".join(quote_lines).strip()


# Build search tokens from the model-produced fact for deterministic quote repair.
def _build_quote_repair_tokens(fact: EvidenceFact) -> list[str]:
    token_sources: list[str] = [fact.name.replace("_", " "), fact.evidence_note]
    if fact.evidence_quote:
        token_sources.append(fact.evidence_quote)

    if isinstance(fact.value, str):
        token_sources.append(fact.value)
    elif isinstance(fact.value, int):
        token_sources.append(str(fact.value))
    elif isinstance(fact.value, list):
        token_sources.extend(item for item in fact.value if isinstance(item, str))

    tokens = _tokenize_for_quote_repair(" ".join(token_sources))
    return [token for token in tokens if len(token) > 1 or token in {"a", "b", "c", "d", "e", "x"}]


# Tokenize text for robust source-line matching during quote repair.
def _tokenize_for_quote_repair(text: str) -> list[str]:
    return re.findall(r"[0-9A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż]+", text.lower())


# Normalize whitespace so quote validation and repair tolerate line-wrap differences.
def _normalize_for_quote_match(text: str) -> str:
    return " ".join(text.split())


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
