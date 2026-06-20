# Deterministic target resolution for the L16 okoeditor task.

from __future__ import annotations

from src.apps.L16_okoeditor.models import OkoState, RecordDetail, TargetSelection


# Resolve the three grounded targets needed by the task.
def resolve_targets(state: OkoState) -> TargetSelection:
    skolwin_incident = resolve_skolwin_incident(state.incident_details)
    skolwin_task = resolve_skolwin_task(state.task_details)
    komarowo_candidate = resolve_komarowo_candidate(
        state.incident_details,
        excluded_ids={skolwin_incident.record_id},
    )
    return TargetSelection(
        skolwin_incident=skolwin_incident,
        skolwin_task=skolwin_task,
        komarowo_candidate=komarowo_candidate,
    )


# Resolve the incident that currently frames Skolwin as human or vehicle activity.
def resolve_skolwin_incident(incidents: tuple[RecordDetail, ...]) -> RecordDetail:
    candidates = [detail for detail in incidents if mentions_skolwin(detail)]
    if not candidates:
        raise ValueError("Could not find the Skolwin incident.")

    candidates.sort(
        key=lambda detail: (
            0 if (detail.code or "").startswith("MOVE") else 1,
            0 if "skolwin" in detail.title.casefold() else 1,
            len(detail.body_text),
            detail.title,
        )
    )
    return candidates[0]


# Resolve the task that mentions Skolwin and still needs completion.
def resolve_skolwin_task(tasks: tuple[RecordDetail, ...]) -> RecordDetail:
    candidates = [detail for detail in tasks if mentions_skolwin(detail)]
    if not candidates:
        raise ValueError("Could not find the Skolwin task.")

    candidates.sort(
        key=lambda detail: (
            0 if detail.is_done is False else 1,
            len(detail.body_text),
            detail.title,
        )
    )
    return candidates[0]


# Resolve the safest unrelated incident that can be repurposed into Komarowo.
def resolve_komarowo_candidate(
    incidents: tuple[RecordDetail, ...],
    *,
    excluded_ids: set[str],
) -> RecordDetail:
    candidates = [detail for detail in incidents if detail.record_id not in excluded_ids]
    if not candidates:
        raise ValueError("Could not find any unrelated incident for Komarowo.")

    candidates.sort(key=incident_replacement_score)
    return candidates[0]


# Return whether one normalized record mentions Skolwin.
def mentions_skolwin(detail: RecordDetail) -> bool:
    haystack = f"{detail.title} {detail.body_text}".casefold()
    return "skolwin" in haystack or "skolwina" in haystack


# Score one incident so the least risky replacement candidate wins.
def incident_replacement_score(detail: RecordDetail) -> tuple[int, int, int, str]:
    text = f"{detail.title} {detail.body_text}".casefold()
    has_city_name = 1 if "miast" in text else 0
    has_destruction_story = 1 if ("zniszcz" in text or "nikt nie przeżył" in text) else 0
    has_human_movement_story = 1 if ("ludzi" in text or "pojazd" in text) else 0
    return (
        has_destruction_story,
        has_city_name + has_human_movement_story,
        len(detail.body_text),
        detail.title,
    )
