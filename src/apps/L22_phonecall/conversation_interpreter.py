# Convert operator transcripts into strict conversation data.

from __future__ import annotations

import re
import unicodedata
from typing import Any, Protocol

from src.apps.L22_phonecall.models import (
    Confidence,
    OperatorIntent,
    OperatorInterpretation,
    RoadStatus,
    VALID_ROAD_IDS,
    build_road_status_set,
)


PASSABLE_WORDS = frozenset(
    {
        "czysta",
        "czysty",
        "clear",
        "dostepna",
        "dostepny",
        "drozn",
        "ok",
        "otwarta",
        "otwarty",
        "przejezdna",
        "przejezdny",
        "wolna",
        "wolny",
    }
)
BLOCKED_WORDS = frozenset(
    {
        "blokada",
        "blocked",
        "nieczynna",
        "nieczynny",
        "nieprzejezdna",
        "nieprzejezdny",
        "odpada",
        "remont",
        "zamknieta",
        "zamkniety",
        "zablokowana",
        "zablokowany",
    }
)
PASSWORD_WORDS = frozenset({"autoryzacja", "haslo", "kod", "password", "uwierzytelnienie"})
REASON_WORDS = frozenset({"cel", "celu", "czemu", "dlaczego", "powod", "sprawie", "uzasadnij", "why"})
MONITORING_WORDS = frozenset({"kamery", "monitoring", "nadzor"})
DISABLED_WORDS = frozenset({"wylaczony", "wylaczone", "wylaczylem", "wylaczylam", "zrobione"})
FAILURE_WORDS = frozenset({"alarm", "odmowa", "rozlaczam", "spalona", "spalone", "wpadka"})
ROAD_MENTION_PATTERN = re.compile(r"\brd[\s-]*(224|472|820)\b")
POLISH_TRANSLATION = str.maketrans(
    {
        "ą": "a",
        "ć": "c",
        "ę": "e",
        "ł": "l",
        "ń": "n",
        "ó": "o",
        "ś": "s",
        "ź": "z",
        "ż": "z",
        "Ą": "A",
        "Ć": "C",
        "Ę": "E",
        "Ł": "L",
        "Ń": "N",
        "Ó": "O",
        "Ś": "S",
        "Ź": "Z",
        "Ż": "Z",
    }
)


# Define the small model boundary used only when deterministic parsing is not enough.
class InterpreterModelProtocol(Protocol):
    # Interpret one transcript and return a JSON-like dictionary.
    def interpret(self, transcript: str, context: dict[str, Any]) -> dict[str, Any]:
        ...


# Convert transcripts through deterministic extraction and an optional model fallback.
class ConversationInterpreter:
    # Store the optional model client and request guard for interpreter calls.
    def __init__(
        self,
        *,
        model_client: InterpreterModelProtocol | None = None,
        max_model_requests: int = 0,
    ) -> None:
        if max_model_requests < 0:
            raise ValueError("max_model_requests must be >= 0.")
        self.model_client = model_client
        self.max_model_requests = max_model_requests
        self._model_requests_used = 0

    # Return how many model-backed interpreter requests have been used.
    def model_requests_used(self) -> int:
        return self._model_requests_used

    # Interpret one operator transcript into a validated object.
    def interpret(self, transcript: str, *, context: dict[str, Any] | None = None) -> OperatorInterpretation:
        deterministic = interpret_deterministically(transcript)
        if deterministic.confidence != Confidence.LOW or self.model_client is None:
            return deterministic

        self._model_requests_used += 1
        if self._model_requests_used > self.max_model_requests:
            raise ValueError("The interpreter request guard was exceeded.")

        raw_output = self.model_client.interpret(
            transcript,
            {
                "deterministic_interpretation": deterministic.to_dict(),
                **(context or {}),
            },
        )
        return parse_model_interpretation(raw_output)


# Normalize Polish text for rule matching while keeping road IDs handled separately.
def normalize_for_matching(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(character for character in decomposed if not unicodedata.combining(character))
    return ascii_text.translate(POLISH_TRANSLATION).lower()


# Return whether any complete or prefix-like keyword is present in normalized text.
def contains_keyword(text: str, keywords: frozenset[str]) -> bool:
    return any(keyword in text for keyword in keywords)


# Parse obvious road status statements without guessing indirect references.
def extract_road_statuses(transcript: str) -> dict[str, RoadStatus]:
    normalized = normalize_for_matching(transcript)
    statuses: dict[str, RoadStatus] = {}
    matches = sorted(ROAD_MENTION_PATTERN.finditer(normalized), key=lambda match: match.start())
    previous_status = RoadStatus.UNKNOWN
    for index, match in enumerate(matches):
        road_id = f"RD{match.group(1)}"
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        context = normalized[match.start() : next_start]
        prefix = normalized[max(0, match.start() - 80) : match.start()]
        status = classify_status_context(context)
        if status == RoadStatus.UNKNOWN and "jedyne" in prefix and "jech" in prefix:
            status = RoadStatus.PASSABLE
        if status == RoadStatus.UNKNOWN and "podobnie" in prefix:
            status = previous_status
        statuses[road_id] = status
        if status != RoadStatus.UNKNOWN:
            previous_status = status
    return {road_id: status for road_id, status in statuses.items() if status != RoadStatus.UNKNOWN}


# Classify the local text around one explicit road ID.
def classify_status_context(context: str) -> RoadStatus:
    if re.search(r"\bnie\s+(jest\s+)?(przejezdn|dostepn|otwart|woln|czyst)", context):
        return RoadStatus.BLOCKED
    if contains_keyword(context, BLOCKED_WORDS):
        return RoadStatus.BLOCKED
    if contains_keyword(context, PASSABLE_WORDS):
        return RoadStatus.PASSABLE
    return RoadStatus.UNKNOWN


# Interpret one transcript using only deterministic rules.
def interpret_deterministically(transcript: str) -> OperatorInterpretation:
    normalized = normalize_for_matching(transcript)
    statuses = extract_road_statuses(transcript)
    asks_for_password = contains_keyword(normalized, PASSWORD_WORDS) and (
        "brzmi" in normalized
        or "jak" in normalized
        or "podaj" in normalized
        or "prosze" in normalized
        or "jaki" in normalized
        or "wymag" in normalized
    )
    asks_for_reason = contains_keyword(normalized, REASON_WORDS)
    confirms_monitoring_disabled = (
        contains_keyword(normalized, MONITORING_WORDS)
        and contains_keyword(normalized, DISABLED_WORDS)
        and "nie wylacz" not in normalized
    )
    mentions_call_failure = contains_keyword(normalized, FAILURE_WORDS)

    intent = infer_intent(
        statuses=statuses,
        asks_for_password=asks_for_password,
        asks_for_reason=asks_for_reason,
        confirms_monitoring_disabled=confirms_monitoring_disabled,
        mentions_call_failure=mentions_call_failure,
    )
    confidence = infer_confidence(
        transcript=transcript,
        statuses=statuses,
        asks_for_password=asks_for_password,
        asks_for_reason=asks_for_reason,
        confirms_monitoring_disabled=confirms_monitoring_disabled,
        mentions_call_failure=mentions_call_failure,
    )
    return OperatorInterpretation(
        intent=intent,
        road_statuses=build_road_status_set({road_id: status for road_id, status in statuses.items()}),
        asks_for_password=asks_for_password,
        asks_for_reason=asks_for_reason,
        confirms_monitoring_disabled=confirms_monitoring_disabled,
        mentions_call_failure=mentions_call_failure,
        confidence=confidence,
        evidence=build_evidence(transcript, intent, statuses),
    )


# Choose the primary operator intent from deterministic signals.
def infer_intent(
    *,
    statuses: dict[str, RoadStatus],
    asks_for_password: bool,
    asks_for_reason: bool,
    confirms_monitoring_disabled: bool,
    mentions_call_failure: bool,
) -> OperatorIntent:
    if mentions_call_failure:
        return OperatorIntent.FAILURE
    if confirms_monitoring_disabled:
        return OperatorIntent.MONITORING_CONFIRMATION
    if asks_for_password:
        return OperatorIntent.PASSWORD_REQUEST
    if asks_for_reason:
        return OperatorIntent.REASON_REQUEST
    if statuses:
        return OperatorIntent.ROAD_STATUS
    return OperatorIntent.OTHER


# Estimate confidence from explicitness, not from model-like bravado.
def infer_confidence(
    *,
    transcript: str,
    statuses: dict[str, RoadStatus],
    asks_for_password: bool,
    asks_for_reason: bool,
    confirms_monitoring_disabled: bool,
    mentions_call_failure: bool,
) -> Confidence:
    if mentions_call_failure or asks_for_password or asks_for_reason or confirms_monitoring_disabled:
        return Confidence.HIGH
    if statuses:
        mentioned_roads = len(ROAD_MENTION_PATTERN.findall(normalize_for_matching(transcript)))
        return Confidence.HIGH if mentioned_roads == len(statuses) else Confidence.MEDIUM
    return Confidence.LOW


# Build a short human-readable evidence note for logs.
def build_evidence(transcript: str, intent: OperatorIntent, statuses: dict[str, RoadStatus]) -> str:
    if statuses:
        status_text = ", ".join(f"{road_id}={status.value}" for road_id, status in sorted(statuses.items()))
        return f"Deterministic parser found explicit road statuses: {status_text}."
    if intent != OperatorIntent.OTHER:
        return f"Deterministic parser matched {intent.value} keywords."
    trimmed = transcript.strip()
    return f"No explicit supported signal found: {trimmed[:120]}"


# Validate one JSON-like model result before the state machine can consume it.
def parse_model_interpretation(raw_output: dict[str, Any]) -> OperatorInterpretation:
    if not isinstance(raw_output, dict):
        raise ValueError("Interpreter model output must be a dictionary.")

    raw_statuses = raw_output.get("road_statuses", {})
    if not isinstance(raw_statuses, dict):
        raise ValueError("road_statuses must be a dictionary.")

    return OperatorInterpretation(
        intent=OperatorIntent(str(raw_output.get("intent", OperatorIntent.OTHER.value))),
        road_statuses=build_road_status_set({str(road_id): str(status) for road_id, status in raw_statuses.items()}),
        asks_for_password=coerce_bool(raw_output.get("asks_for_password", False), "asks_for_password"),
        asks_for_reason=coerce_bool(raw_output.get("asks_for_reason", False), "asks_for_reason"),
        confirms_monitoring_disabled=coerce_bool(
            raw_output.get("confirms_monitoring_disabled", False),
            "confirms_monitoring_disabled",
        ),
        mentions_call_failure=coerce_bool(raw_output.get("mentions_call_failure", False), "mentions_call_failure"),
        confidence=Confidence(str(raw_output.get("confidence", Confidence.LOW.value))),
        evidence=str(raw_output.get("evidence", "Model interpretation validated.")),
    )


# Convert only real booleans to avoid accepting stringly model output silently.
def coerce_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean.")
    return value
