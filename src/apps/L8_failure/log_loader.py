# Read and parse the large L8 source log without involving the model.

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from src.apps.L8_failure.models import LogEvent, LogProfile
from src.apps.L8_failure.token_budget import estimate_tokens


LOG_LINE_PATTERN = re.compile(
    r"^\[(?P<timestamp>\d{4}-\d{2}-\d{2} \d{1,2}:\d{2})(?::\d{2})?\]\s+"
    r"\[(?P<level>[A-Z]+)\]\s+"
    r"(?P<message>.+)$"
)
COMPONENT_PATTERN = re.compile(r"\b[A-Z][A-Z0-9]{2,}\b")
IGNORED_COMPONENT_TOKENS = {"INFO", "WARN", "ERRO", "ERROR", "CRIT", "DEBUG", "TRACE"}


# Extract the first component-like token from one parsed message.
def extract_component_id(message: str) -> str:
    for match in COMPONENT_PATTERN.finditer(message):
        token = match.group(0)
        if token not in IGNORED_COMPONENT_TOKENS:
            return token

    return "UNKNOWN"


# Parse one raw log line into a traceable event, or return None for invalid lines.
def parse_log_line(source_line: int, raw_line: str) -> LogEvent | None:
    text = raw_line.strip()
    match = LOG_LINE_PATTERN.match(text)
    if match is None:
        return None

    message = match.group("message")
    return LogEvent(
        source_line=source_line,
        timestamp=match.group("timestamp"),
        level=match.group("level"),
        component_id=extract_component_id(message),
        message=message,
        raw_text=text,
    )


# Load every parseable source event while keeping line numbers stable.
def load_log_events(log_file: Path) -> tuple[list[LogEvent], int, int]:
    if not log_file.exists():
        raise FileNotFoundError(f"Source log file does not exist: {log_file}")
    if not log_file.is_file():
        raise ValueError(f"Source log path is not a file: {log_file}")

    events: list[LogEvent] = []
    parse_failures = 0
    characters_count = 0

    with log_file.open("r", encoding="utf-8") as file:
        for source_line, raw_line in enumerate(file, start=1):
            characters_count += len(raw_line)
            event = parse_log_line(source_line, raw_line)
            if event is None:
                parse_failures += 1
                continue
            events.append(event)

    return events, parse_failures, characters_count


# Build a compact profile so the run report explains the source file shape.
def build_log_profile(log_file: Path, events: list[LogEvent], parse_failures: int, characters_count: int) -> LogProfile:
    levels = Counter(event.level for event in events)
    component_ids = Counter(event.component_id for event in events)

    return LogProfile(
        path=str(log_file),
        lines_count=len(events) + parse_failures,
        characters_count=characters_count,
        estimated_tokens=estimate_tokens(log_file.read_text(encoding="utf-8")),
        levels=dict(sorted(levels.items())),
        component_ids=dict(component_ids.most_common(50)),
        parse_failures=parse_failures,
    )
