# Run report rendering for the L4 sendit MVP2 Stage 1-4 workflow.

from src.apps.L4_sendit.L4_sendit_MVP2.models import (
    EvidencePackage,
    ReferenceInventoryItem,
    SelectedSources,
    TaskResult,
    TaskUnderstanding,
    ValidationResult,
)


# Build a short human-readable report for the Stage 1-4 run.
def build_run_report(
    command_file: str,
    task_understanding: TaskUnderstanding,
    task_understanding_validation_results: list[ValidationResult],
    reference_inventory: list[ReferenceInventoryItem],
    reference_inventory_validation_results: list[ValidationResult],
    selected_sources: SelectedSources | None,
    selected_sources_validation_results: list[ValidationResult],
    evidence_package: EvidencePackage | None,
    evidence_validation_results: list[ValidationResult],
    task_result: TaskResult | None,
    task_result_validation_results: list[ValidationResult],
    model_source: str,
    source_selection_model_source: str | None,
    evidence_extraction_model_source: str | None,
    task_execution_source: str | None,
) -> str:
    task_validation_lines = [
        f"- {validation_result.status}: {validation_result.message}"
        for validation_result in task_understanding_validation_results
    ]
    inventory_validation_lines = [
        f"- {validation_result.status}: {validation_result.message}"
        for validation_result in reference_inventory_validation_results
    ]
    source_selection_validation_lines = [
        f"- {validation_result.status}: {validation_result.message}"
        for validation_result in selected_sources_validation_results
    ] or ["- not run"]
    evidence_validation_lines = [
        f"- {validation_result.status}: {validation_result.message}"
        for validation_result in evidence_validation_results
    ] or ["- not run"]
    task_result_validation_lines = [
        f"- {validation_result.status}: {validation_result.message}"
        for validation_result in task_result_validation_results
    ] or ["- not run"]
    documentation_need_lines = [
        f"- `{documentation_need.need}`: {documentation_need.reason}"
        for documentation_need in task_understanding.documentation_needs
    ] or ["- none"]
    inventory_lines = [
        f"- `{inventory_item.path}` | `{inventory_item.source_type}` | `{inventory_item.size_bytes}` bytes | {inventory_item.hint}"
        for inventory_item in reference_inventory
    ] or ["- none"]
    missing_input_lines = [
        f"- `{missing_input}`"
        for missing_input in task_understanding.missing_inputs
    ] or ["- none"]
    uncertainty_lines = [
        f"- {uncertainty_note}"
        for uncertainty_note in task_understanding.uncertainty_notes
    ] or ["- none"]
    selected_source_lines = _build_selected_source_lines(selected_sources)
    missing_source_lines = _build_missing_source_lines(selected_sources)
    selection_uncertainty_lines = _build_selection_uncertainty_lines(selected_sources)
    evidence_fact_lines = _build_evidence_fact_lines(evidence_package)
    missing_fact_lines = _build_missing_fact_lines(evidence_package)
    conflict_lines = _build_conflict_lines(evidence_package)
    task_result_lines = _build_task_result_lines(task_result)
    task_uncertainty_lines = _build_task_result_uncertainty_lines(task_result)

    return "\n".join(
        [
            "# L4 Sendit MVP2 Stage 1-5 Run Report",
            "",
            "## Task Understanding",
            f"- Command file: `{command_file}`",
            f"- Model source: `{model_source}`",
            f"- task_name: `{task_understanding.task_name}`",
            f"- expected_output_kind: `{task_understanding.expected_output_kind}`",
            f"- domain: `{task_understanding.domain}`",
            f"- confidence: `{task_understanding.confidence}`",
            "",
            "## Task Understanding Validation",
            *task_validation_lines,
            "",
            "## Reference Inventory",
            *inventory_lines,
            "",
            "## Reference Inventory Validation",
            *inventory_validation_lines,
            "",
            "## Selected Sources",
            f"- Model source: `{source_selection_model_source or 'not run'}`",
            *selected_source_lines,
            "",
            "## Source Selection Validation",
            *source_selection_validation_lines,
            "",
            "## Evidence Package",
            f"- Model source: `{evidence_extraction_model_source or 'not run'}`",
            *evidence_fact_lines,
            "",
            "## Evidence Validation",
            *evidence_validation_lines,
            "",
            "## Task Result",
            f"- Execution source: `{task_execution_source or 'not run'}`",
            *task_result_lines,
            "",
            "## Task Result Validation",
            *task_result_validation_lines,
            "",
            "## Documentation Needs",
            *documentation_need_lines,
            "",
            "## Missing Inputs",
            *missing_input_lines,
            "",
            "## Uncertainty Notes",
            *uncertainty_lines,
            "",
            "## Missing Sources",
            *missing_source_lines,
            "",
            "## Source Selection Uncertainty Notes",
            *selection_uncertainty_lines,
            "",
            "## Missing Facts",
            *missing_fact_lines,
            "",
            "## Evidence Conflicts",
            *conflict_lines,
            "",
            "## Task Result Uncertainty Notes",
            *task_uncertainty_lines,
        ]
    )


# Build report lines for selected Stage 3 sources.
def _build_selected_source_lines(selected_sources: SelectedSources | None) -> list[str]:
    if selected_sources is None:
        return ["- not run"]

    lines = [
        (
            f"- `{source.path}` | `{source.source_type}` | "
            f"`{source.documentation_need}` | `{source.intended_use}` | "
            f"confidence `{source.confidence}` | {source.reason}"
        )
        for source in selected_sources.selected_sources
    ]
    rejected_lines = [
        f"- rejected `{source.path}`: {source.reason}"
        for source in selected_sources.rejected_sources
    ]

    return lines + rejected_lines or ["- none"]


# Build report lines for Stage 3 missing sources.
def _build_missing_source_lines(selected_sources: SelectedSources | None) -> list[str]:
    if selected_sources is None:
        return ["- not run"]

    return [f"- {missing_source}" for missing_source in selected_sources.missing_sources] or ["- none"]


# Build report lines for Stage 3 uncertainty notes.
def _build_selection_uncertainty_lines(selected_sources: SelectedSources | None) -> list[str]:
    if selected_sources is None:
        return ["- not run"]

    return [f"- {note}" for note in selected_sources.uncertainty_notes] or ["- none"]


# Build report lines for extracted evidence facts.
def _build_evidence_fact_lines(evidence_package: EvidencePackage | None) -> list[str]:
    if evidence_package is None:
        return ["- not run"]

    return [
        (
            f"- `{fact.name}` from `{fact.source_path}` | `{fact.source_type}` | "
            f"`{fact.evidence_kind}` | confidence `{fact.confidence}` | {fact.evidence_note}"
        )
        for fact in evidence_package.facts
    ] or ["- none"]


# Build report lines for missing facts.
def _build_missing_fact_lines(evidence_package: EvidencePackage | None) -> list[str]:
    if evidence_package is None:
        return ["- not run"]

    return [f"- {missing_fact}" for missing_fact in evidence_package.missing_facts] or ["- none"]


# Build report lines for evidence conflicts.
def _build_conflict_lines(evidence_package: EvidencePackage | None) -> list[str]:
    if evidence_package is None:
        return ["- not run"]

    return [f"- {conflict}" for conflict in evidence_package.conflicts] or ["- none"]


# Build report lines for the Stage 5 structured task result.
def _build_task_result_lines(task_result: TaskResult | None) -> list[str]:
    if task_result is None:
        return ["- not run"]

    result = task_result.result
    return [
        f"- task_name: `{task_result.task_name}`",
        f"- result_kind: `{task_result.result_kind}`",
        f"- route_code: `{result.route_code}`",
        f"- category: `{result.category}`",
        f"- wdp: `{result.wdp}`",
        f"- amount_due_pp: `{result.amount_due_pp}`",
    ]


# Build report lines for Stage 5 uncertainty notes.
def _build_task_result_uncertainty_lines(task_result: TaskResult | None) -> list[str]:
    if task_result is None:
        return ["- not run"]

    return [f"- {note}" for note in task_result.uncertainty_notes] or ["- none"]
