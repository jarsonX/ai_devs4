from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Represents one goods row downloaded from the categorize CSV.
@dataclass(frozen=True)
class GoodsItem:
    item_id: str
    description: str


# Represents one raw response returned by the hub.
@dataclass(frozen=True)
class HubResponse:
    status_code: int
    payload: Any | None
    text: str


# Represents one prompt submission for a single goods item.
@dataclass(frozen=True)
class ItemVerification:
    item: GoodsItem
    prompt: str
    response: HubResponse


# Represents one chronological event stored in the run report.
@dataclass(frozen=True)
class RunLogEntry:
    timestamp: str
    step: str
    message: str
    request: dict[str, Any] | None = None
    response: HubResponse | None = None
    item: GoodsItem | None = None
    details: dict[str, Any] = field(default_factory=dict)


# Represents the collected result of one full categorize attempt.
@dataclass
class RunReport:
    task: str = "categorize"
    started_at: str | None = None
    ended_at: str | None = None
    items_count: int = 0
    events: list[RunLogEntry] = field(default_factory=list)
    verifications: list[ItemVerification] = field(default_factory=list)
    success: bool = False
    flag: str | None = None
    error_summary: str | None = None
