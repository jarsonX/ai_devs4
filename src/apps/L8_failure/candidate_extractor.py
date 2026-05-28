# Deterministic first-pass filtering for likely failure-related log events.

from __future__ import annotations

from src.apps.L8_failure.models import LogEvent


IMPORTANT_LEVELS = {"WARN", "ERRO", "ERROR", "CRIT"}
LOW_SEVERITY_CONTEXT_KEYWORDS = {
    "auxiliary",
    "boundary",
    "constrained",
    "correction",
    "critical",
    "degraded",
    "emergency",
    "exceeded",
    "fault",
    "interlock",
    "margin",
    "no longer",
    "reactor",
    "recovery",
    "reserve",
    "ripple",
    "threshold",
    "trip",
    "unstable",
    "validation",
    "watchdog",
}


# Decide whether one event deserves a model review pass.
def is_candidate_event(event: LogEvent) -> bool:
    if event.level in IMPORTANT_LEVELS:
        return True

    haystack = f"{event.component_id} {event.message}".lower()
    return any(keyword in haystack for keyword in LOW_SEVERITY_CONTEXT_KEYWORDS)


# Build a compact candidate list by keeping the first occurrence of each event type.
def extract_candidates(events: list[LogEvent]) -> list[LogEvent]:
    candidates: list[LogEvent] = []
    seen_event_keys: set[tuple[str, str, str]] = set()

    for event in events:
        if not is_candidate_event(event):
            continue

        event_key = (event.level, event.component_id, event.message)
        if event_key in seen_event_keys:
            continue

        candidates.append(event)
        seen_event_keys.add(event_key)

    return candidates
