# Deterministic Stage 6 validation and rendering for supported output kinds.

from datetime import date
from pathlib import Path
import re
from typing import Any

from src.apps.L4_sendit.L4_sendit_MVP2.models import (
    EvidencePackage,
    RenderedOutputResult,
    TaskResult,
    TaskUnderstanding,
)


# Render the final output artifact for the current supported output kind.
def render_final_output(
    task_understanding: TaskUnderstanding,
    task_result: TaskResult,
    evidence_package: EvidencePackage,
    repo_root: Path,
) -> RenderedOutputResult:
    if task_understanding.expected_output_kind == "declaration_text":
        declaration_text = _render_declaration_text(
            task_result=task_result,
            evidence_package=evidence_package,
            repo_root=repo_root,
            render_date=date.today().isoformat(),
        )
        return RenderedOutputResult(
            output_kind="declaration_text",
            final_output_text=declaration_text,
            final_output_json=None,
            compatibility_declaration_text=declaration_text,
        )

    if task_understanding.expected_output_kind == "json":
        return RenderedOutputResult(
            output_kind="json",
            final_output_text=None,
            final_output_json=task_result.model_dump(mode="json"),
            compatibility_declaration_text=None,
        )

    raise ValueError(
        f"Stage 6 does not support expected_output_kind: {task_understanding.expected_output_kind}"
    )


# Render the known declaration text from the selected declaration template source.
def _render_declaration_text(
    task_result: TaskResult,
    evidence_package: EvidencePackage,
    repo_root: Path,
    render_date: str,
) -> str:
    template_source_path = _require_fact_source_path(evidence_package, "declaration_template_fields")
    template_markdown = (repo_root / template_source_path).resolve().read_text(encoding="utf-8")
    template_block = _extract_template_block(template_markdown)
    declaration_data = task_result.result

    rendered_lines: list[str] = []
    for line in template_block.splitlines():
        rendered_lines.append(
            _render_template_line(
                line=line,
                replacements={
                    "DATA": render_date,
                    "PUNKT NADAWCZY": declaration_data.origin_point,
                    "NADAWCA": declaration_data.sender_identifier,
                    "PUNKT DOCELOWY": declaration_data.destination_point,
                    "TRASA": declaration_data.route_code,
                    "KATEGORIA PRZESYŁKI": declaration_data.category,
                    "OPIS ZAWARTOŚCI (max 200 znaków)": declaration_data.contents,
                    "DEKLAROWANA MASA (kg)": str(declaration_data.declared_weight_kg),
                    "WDP": str(declaration_data.wdp),
                    "UWAGI SPECJALNE": declaration_data.special_notes,
                    "KWOTA DO ZAPŁATY": f"{declaration_data.amount_due_pp} PP",
                },
            )
        )

    return "\n".join(rendered_lines).strip() + "\n"


# Extract the fenced declaration template block from the markdown source.
def _extract_template_block(template_markdown: str) -> str:
    code_block_match = re.search(r"```(?:\r?\n)(.*?)(?:\r?\n)```", template_markdown, re.DOTALL)
    if code_block_match is None:
        raise ValueError("Declaration template source does not contain a fenced code block.")

    return code_block_match.group(1).strip("\r\n")


# Render one declaration template line using deterministic field replacements.
def _render_template_line(line: str, replacements: dict[str, str]) -> str:
    field_separator = ": "
    if field_separator not in line:
        return line

    field_label, _field_value = line.split(field_separator, 1)
    replacement_value = replacements.get(field_label)
    if replacement_value is None:
        return line

    return f"{field_label}: {replacement_value}"


# Read one required fact source path from the validated evidence package.
def _require_fact_source_path(evidence_package: EvidencePackage, fact_name: str) -> str:
    for fact in evidence_package.facts:
        if fact.name == fact_name:
            return fact.source_path

    raise ValueError(f"Required evidence fact is missing: {fact_name}")
