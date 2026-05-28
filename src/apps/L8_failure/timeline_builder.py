# Build a compact one-event-per-line timeline from validated classified events.

from __future__ import annotations

import re

from src.apps.L8_failure.models import ClassifiedEvent
from src.apps.L8_failure.token_budget import estimate_tokens


TIMELINE_PATTERN = re.compile(
    r"^\[\d{4}-\d{2}-\d{2} \d{1,2}:\d{2}\] "
    r"\[[A-Z]+\] "
    r"[A-Z][A-Z0-9_:-]*: .+$"
)
LEVEL_PRIORITY = {"CRIT": 0, "ERRO": 1, "ERROR": 1, "WARN": 2, "INFO": 3}
RELEVANCE_PRIORITY = {"direct_failure_chain": 0, "supporting_context": 1, "probably_noise": 2}


# Convert one validated classified event into the exact final line shape.
def format_timeline_line(event: ClassifiedEvent) -> str:
    return f"[{event.timestamp}] [{event.level}] {event.component_id}: {event.summary}"


# Check that one final answer line still has the expected event shape.
def validate_timeline_line(line: str) -> None:
    if "\n" in line or "\r" in line:
        raise ValueError("Timeline line must not contain embedded newlines.")
    if TIMELINE_PATTERN.match(line) is None:
        raise ValueError(f"Invalid timeline line format: {line}")


# Sort events chronologically while keeping the most useful events first when trimming.
def event_priority(event: ClassifiedEvent) -> tuple[int, int, str, int]:
    return (
        RELEVANCE_PRIORITY.get(event.relevance, 9),
        LEVEL_PRIORITY.get(event.level, 9),
        event.timestamp,
        event.source_line,
    )


# Build the best timeline that fits the target token budget before Hub submission.
def build_condensed_timeline(
    events: list[ClassifiedEvent],
    *,
    target_token_limit: int,
    hard_token_limit: int,
) -> tuple[str, int, list[ClassifiedEvent]]:
    useful_events = [
        event
        for event in events
        if event.relevance in {"direct_failure_chain", "supporting_context"}
    ]
    ranked_events = sorted(useful_events, key=event_priority)

    selected_events = list(ranked_events)
    while selected_events:
        timeline_events = sorted(selected_events, key=lambda event: (event.timestamp, event.source_line))
        lines = [format_timeline_line(event) for event in timeline_events]
        for line in lines:
            validate_timeline_line(line)

        answer = "\n".join(lines)
        token_estimate = estimate_tokens(answer)
        if token_estimate <= target_token_limit:
            return answer, token_estimate, timeline_events

        selected_events.pop()

    answer = ""
    token_estimate = estimate_tokens(answer)
    if token_estimate > hard_token_limit:
        raise ValueError("Unable to build a timeline within the hard token limit.")

    return answer, token_estimate, []
