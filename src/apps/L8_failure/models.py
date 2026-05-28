from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


Severity = Literal["INFO", "WARN", "ERRO", "ERROR", "CRIT", "DEBUG", "TRACE", "UNKNOWN"]
Subsystem = Literal["power", "cooling", "water_pump", "software", "safety", "sensor", "unknown", "other"]
Relevance = Literal["direct_failure_chain", "supporting_context", "probably_noise"]


# Store one parsed source log line with the raw text kept for traceability.
@dataclass(frozen=True)
class LogEvent:
    source_line: int
    timestamp: str
    level: str
    component_id: str
    message: str
    raw_text: str


# Store basic file facts so large-input decisions are visible in reports.
@dataclass(frozen=True)
class LogProfile:
    path: str
    lines_count: int
    characters_count: int
    estimated_tokens: int
    levels: dict[str, int]
    component_ids: dict[str, int]
    parse_failures: int


# Store a bounded search result that can safely be shown to the model.
@dataclass(frozen=True)
class SearchResult:
    query: dict[str, Any]
    total_matches: int
    returned_matches: int
    events: list[LogEvent]


# Store one model-validated event ready for timeline construction.
@dataclass(frozen=True)
class ClassifiedEvent:
    source_line: int
    timestamp: str
    level: str
    component_id: str
    subsystem: str
    relevance: str
    summary: str
    raw_text: str


# Store one raw response returned by the Hub verifier.
@dataclass(frozen=True)
class HubResponse:
    status_code: int
    payload: Any | None
    text: str


# Store one chronological event in the run report.
@dataclass(frozen=True)
class RunLogEntry:
    timestamp: str
    step: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    request: dict[str, Any] | None = None
    response: HubResponse | None = None


# Store the collected result of one L8 attempt for later debugging.
@dataclass
class RunReport:
    task: str = "failure"
    started_at: str | None = None
    ended_at: str | None = None
    success: bool = False
    flag: str | None = None
    error_summary: str | None = None
    events: list[RunLogEntry] = field(default_factory=list)
    profile: LogProfile | None = None
    candidates_count: int = 0
    classified_events_count: int = 0
    condensed_token_estimate: int | None = None
    model_requests_used: int = 0
    verify_requests_used: int = 0
