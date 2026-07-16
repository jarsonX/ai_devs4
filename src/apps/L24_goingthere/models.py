# Data models shared by the L24 goingthere workflow.

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


FLAG_PREFIX = "".join(chr(value) for value in (70, 76, 71))
FLAG_PATTERN = re.compile(r"\{" + FLAG_PREFIX + r":[^}]+\}")
REDACTED = "***REDACTED***"


# Enumerate the three movement commands accepted by the Hub.
class MovementCommand(str, Enum):
    LEFT = "left"
    GO = "go"
    RIGHT = "right"


# Enumerate relative rock directions described by radio hints.
class RockDirection(str, Enum):
    LEFT = "left"
    FRONT = "front"
    RIGHT = "right"


# Store the current server-confirmed position and visible current-column rock.
@dataclass(frozen=True)
class GameState:
    player_row: int
    player_col: int
    base_row: int
    current_stone_row: int


# Store a successfully parsed active radar trap.
@dataclass(frozen=True)
class RadarTrap:
    frequency: int
    detection_code: str


# Mark a scanner result that confirms no active radar trap.
@dataclass(frozen=True)
class RadarClear:
    clear: bool = True


RadarReading = RadarClear | RadarTrap


# Store one decoded or raw HTTP response.
@dataclass(frozen=True)
class ApiResponse:
    status_code: int
    payload: Any | None
    text: str


# Store one masked request attempt and its full response.
@dataclass(frozen=True)
class LoggedExchange:
    sequence: int
    action: str
    attempt: int
    request: dict[str, Any]
    response: ApiResponse

    # Convert the exchange into JSON-safe runtime output.
    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "action": self.action,
            "attempt": self.attempt,
            "request": self.request,
            "response": {
                "status_code": self.response.status_code,
                "payload": self.response.payload,
                "text": self.response.text,
                "flag_found": response_contains_flag(self.response),
            },
        }


# Store the result of one accepted, crashed, or winning movement command.
@dataclass(frozen=True)
class MoveOutcome:
    state: GameState | None
    crashed: bool
    finished: bool
    flag: str | None
    response: ApiResponse
    reconciled_from_preview: bool = False


# Store the official preview backend's current game snapshot.
@dataclass(frozen=True)
class PreviewState:
    state: GameState | None
    active: bool
    crashed: bool
    finished: bool
    flag: str | None


# Return whether one response contains a course flag.
def response_contains_flag(response: ApiResponse) -> bool:
    haystack = response.text
    if response.payload is not None:
        haystack = f"{haystack}\n{json.dumps(response.payload, ensure_ascii=False)}"
    return FLAG_PATTERN.search(haystack) is not None


# Extract the visible course flag without treating it as a repository secret.
def extract_flag(response: ApiResponse) -> str | None:
    haystack = response.text
    if response.payload is not None:
        haystack = f"{haystack}\n{json.dumps(response.payload, ensure_ascii=False)}"
    match = FLAG_PATTERN.search(haystack)
    return match.group(0) if match else None


# Mask the API key before preserving request metadata.
def mask_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    masked = dict(payload)
    if "apikey" in masked:
        masked["apikey"] = REDACTED
    if "key" in masked:
        masked["key"] = REDACTED
    return masked
