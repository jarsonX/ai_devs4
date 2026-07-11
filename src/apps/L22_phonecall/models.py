# Data models shared by the L22 phonecall workflow.

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


FLAG_PREFIX = "".join(chr(value) for value in (70, 76, 71))
FLAG_PATTERN = re.compile(r"\{" + FLAG_PREFIX + r":[^}]+\}")
VALID_ROAD_IDS = frozenset({"RD224", "RD472", "RD820"})


# Enumerate the road identifiers known to the task.
class RoadId(StrEnum):
    RD224 = "RD224"
    RD472 = "RD472"
    RD820 = "RD820"


# Enumerate the stable road status values accepted by the state machine.
class RoadStatus(StrEnum):
    PASSABLE = "passable"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


# Enumerate operator-turn intents produced by the interpreter.
class OperatorIntent(StrEnum):
    ROAD_STATUS = "road_status"
    PASSWORD_REQUEST = "password_request"
    REASON_REQUEST = "reason_request"
    MONITORING_CONFIRMATION = "monitoring_confirmation"
    CLARIFICATION = "clarification"
    FAILURE = "failure"
    OTHER = "other"


# Enumerate confidence values for model or parser interpretations.
class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Enumerate the conversation states controlled by deterministic code.
class ConversationState(StrEnum):
    NEW = "NEW"
    STARTED = "STARTED"
    ASKED_ROAD_STATUS = "ASKED_ROAD_STATUS"
    AUTH_CHALLENGE = "AUTH_CHALLENGE"
    ROAD_STATUS_KNOWN = "ROAD_STATUS_KNOWN"
    MONITORING_REQUESTED = "MONITORING_REQUESTED"
    REASON_CHALLENGE = "REASON_CHALLENGE"
    MONITORING_CONFIRMED = "MONITORING_CONFIRMED"
    FAILED = "FAILED"


# Enumerate the only speech acts the assistant may perform.
class SpeechAct(StrEnum):
    START_SESSION = "start_session"
    ASK_ROAD_STATUS = "ask_road_status"
    PROVIDE_PASSWORD = "provide_password"
    WAIT_FOR_STATUS = "wait_for_status"
    CLARIFY_STATUS = "clarify_status"
    REQUEST_MONITORING_DISABLE = "request_monitoring_disable"
    EXPLAIN_FOOD_TRANSPORT = "explain_food_transport"
    WAIT_FOR_CONFIRMATION = "wait_for_confirmation"
    CLARIFY_MONITORING = "clarify_monitoring"
    FINISH = "finish"
    RESTART_SESSION = "restart_session"


# Store one decoded or raw HTTP response.
@dataclass(frozen=True)
class ApiResponse:
    status_code: int
    payload: Any | None
    text: str


# Store one masked request and full response for runtime artifacts.
@dataclass(frozen=True)
class LoggedExchange:
    sequence: int
    action: str
    request: dict[str, Any]
    response: ApiResponse

    # Convert the exchange into JSON-safe output.
    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "action": self.action,
            "request": self.request,
            "response": {
                "status_code": self.response.status_code,
                "payload": self.response.payload,
                "text": self.response.text,
                "flag_found": response_contains_flag(self.response),
            },
        }


# Store validated road statuses for one operator turn or call state snapshot.
@dataclass(frozen=True)
class RoadStatusSet:
    statuses: dict[str, RoadStatus] = field(
        default_factory=lambda: {road_id: RoadStatus.UNKNOWN for road_id in sorted(VALID_ROAD_IDS)}
    )

    # Return roads currently considered passable.
    def passable_roads(self) -> list[str]:
        return [
            road_id
            for road_id in sorted(VALID_ROAD_IDS)
            if self.statuses.get(road_id, RoadStatus.UNKNOWN) == RoadStatus.PASSABLE
        ]

    # Convert the status set into JSON-safe output.
    def to_dict(self) -> dict[str, str]:
        return {road_id: self.statuses.get(road_id, RoadStatus.UNKNOWN).value for road_id in sorted(VALID_ROAD_IDS)}


# Store the strict interpretation of one operator turn.
@dataclass(frozen=True)
class OperatorInterpretation:
    intent: OperatorIntent
    road_statuses: RoadStatusSet
    asks_for_password: bool
    asks_for_reason: bool
    confirms_monitoring_disabled: bool
    mentions_call_failure: bool
    confidence: Confidence
    evidence: str

    # Convert the interpretation into JSON-safe output.
    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent.value,
            "road_statuses": self.road_statuses.to_dict(),
            "asks_for_password": self.asks_for_password,
            "asks_for_reason": self.asks_for_reason,
            "confirms_monitoring_disabled": self.confirms_monitoring_disabled,
            "mentions_call_failure": self.mentions_call_failure,
            "confidence": self.confidence.value,
            "evidence": self.evidence,
        }


# Store the assistant's approved next speech act and text.
@dataclass(frozen=True)
class AssistantPlan:
    speech_act: SpeechAct
    utterance: str
    roads: list[str]
    note: str

    # Convert the plan into JSON-safe output.
    def to_dict(self) -> dict[str, Any]:
        return {
            "speech_act": self.speech_act.value,
            "utterance": self.utterance,
            "roads": list(self.roads),
            "note": self.note,
        }


# Store a compact summary of one call attempt.
@dataclass(frozen=True)
class CallReport:
    call_id: str
    final_state: ConversationState
    flag_found: bool
    turns: int
    hub_requests_used: int
    mode: str | None = None
    stt_requests_used: int = 0
    interpreter_requests_used: int = 0
    planner_requests_used: int = 0
    tts_requests_used: int = 0
    selected_roads: list[str] = field(default_factory=list)
    error_summary: str | None = None

    # Convert the report into JSON-safe output.
    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["final_state"] = self.final_state.value
        return data


# Return whether one response contains a course flag anywhere visible.
def response_contains_flag(response: ApiResponse) -> bool:
    haystack = response.text
    if response.payload is not None:
        haystack = f"{haystack}\n{json.dumps(response.payload, ensure_ascii=False)}"
    return FLAG_PATTERN.search(haystack) is not None


# Normalize one road status mapping while rejecting unknown road IDs.
def build_road_status_set(raw_statuses: dict[str, str | RoadStatus]) -> RoadStatusSet:
    statuses = {road_id: RoadStatus.UNKNOWN for road_id in sorted(VALID_ROAD_IDS)}
    for road_id, raw_status in raw_statuses.items():
        if road_id not in VALID_ROAD_IDS:
            raise ValueError(f"Unsupported road id: {road_id}")
        statuses[road_id] = raw_status if isinstance(raw_status, RoadStatus) else RoadStatus(raw_status)
    return RoadStatusSet(statuses=statuses)
