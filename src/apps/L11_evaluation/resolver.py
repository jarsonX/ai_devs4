# Final anomaly resolution for the L11 evaluation workflow.

from __future__ import annotations

from src.apps.L11_evaluation.models import (
    EvaluationAnswer,
    MeasurementFinding,
    NoteClassification,
    SensorIssue,
)


# Build one semantic contradiction issue when notes claim everything is fine.
def build_claims_ok_but_data_invalid_issue(file_id: str) -> SensorIssue:
    return SensorIssue(
        file_id=file_id,
        kind="operator_claims_ok_but_data_invalid",
        message="Operator note claims the readings are OK, but deterministic validation found invalid data.",
    )


# Build one semantic contradiction issue when notes claim an error but data is valid.
def build_claims_error_but_data_ok_issue(file_id: str) -> SensorIssue:
    return SensorIssue(
        file_id=file_id,
        kind="operator_claims_error_but_data_ok",
        message="Operator note claims there is an error, but deterministic validation found valid data.",
    )


# Return semantic contradiction issues for one file after deterministic validation is already known.
def resolve_note_contradiction_issues(
    finding: MeasurementFinding,
    note_classification: NoteClassification,
) -> list[SensorIssue]:
    if not finding.measurements_ok and note_classification.label == "claims_ok":
        return [build_claims_ok_but_data_invalid_issue(finding.file_id)]

    if finding.measurements_ok and note_classification.label == "claims_error":
        return [build_claims_error_but_data_ok_issue(finding.file_id)]

    return []


# Merge deterministic issues and semantic contradiction issues for one resolved file.
def resolve_finding_issues(
    finding: MeasurementFinding,
    note_classification: NoteClassification,
) -> list[SensorIssue]:
    return [
        *finding.issues,
        *resolve_note_contradiction_issues(finding, note_classification),
    ]


# Return the final sorted file IDs that should be rechecked.
def resolve_recheck_ids(
    findings: list[MeasurementFinding],
    note_classifications_by_file_id: dict[str, NoteClassification],
) -> list[str]:
    recheck_ids: list[str] = []

    for finding in findings:
        note_classification = note_classifications_by_file_id.get(finding.file_id)
        if note_classification is None:
            raise ValueError(
                f"Missing note classification for file_id {finding.file_id}."
            )

        resolved_issues = resolve_finding_issues(finding, note_classification)
        if resolved_issues:
            recheck_ids.append(finding.file_id)

    return sorted(recheck_ids)


# Build the final answer payload before the Hub request adds the real API key.
def build_evaluation_answer(
    findings: list[MeasurementFinding],
    note_classifications_by_file_id: dict[str, NoteClassification],
) -> EvaluationAnswer:
    return EvaluationAnswer(
        recheck=resolve_recheck_ids(findings, note_classifications_by_file_id),
    )
