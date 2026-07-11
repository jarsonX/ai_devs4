# Validation helpers for assistant utterances before text-to-speech.

from __future__ import annotations

import re
from dataclasses import dataclass

from src.apps.L22_phonecall.models import SpeechAct, VALID_ROAD_IDS
from src.apps.L22_phonecall.state_machine import PASSWORD


ROAD_PATTERN = re.compile(r"\bRD\d{3}\b")
FORBIDDEN_TERMS = (
    "syjon",
    "przerzut",
    "przerzutu",
    "ludzi",
    "większej grupy",
    "wiekszej grupy",
)
POLISH_SIGNAL_WORDS = (
    "dzień",
    "dzien",
    "dobry",
    "proszę",
    "prosze",
    "potrzebuję",
    "potrzebuje",
    "statusu",
    "dróg",
    "drog",
    "rozumiem",
    "monitoring",
    "transport",
    "jedzenia",
    "jedzenie",
    "żywności",
    "zywnosci",
    "potwierdź",
    "potwierdz",
    "dziękuję",
    "dziekuje",
)


# Preserve local validation results in a log-friendly structure.
@dataclass(frozen=True)
class UtteranceValidationResult:
    passed: bool
    issues: list[str]


# Check one assistant utterance before it can be converted to audio.
def validate_utterance(
    utterance: str,
    speech_act: SpeechAct,
    *,
    allowed_roads: list[str] | tuple[str, ...] = (),
    max_words: int,
) -> UtteranceValidationResult:
    issues: list[str] = []
    cleaned = utterance.strip()
    lowered = cleaned.lower()
    allowed_road_set = set(allowed_roads)

    if not cleaned:
        issues.append("utterance is empty.")
        return UtteranceValidationResult(False, issues)

    words = cleaned.split()
    if len(words) > max_words:
        issues.append(f"utterance exceeds {max_words} words.")

    if not looks_polish_or_password(cleaned):
        issues.append("utterance does not look like a Polish phone message.")

    for forbidden_term in FORBIDDEN_TERMS:
        if forbidden_term in lowered:
            issues.append(f"utterance contains forbidden term: {forbidden_term}.")

    mentioned_roads = ROAD_PATTERN.findall(cleaned)
    for road_id in mentioned_roads:
        if road_id not in VALID_ROAD_IDS:
            issues.append(f"utterance mentions unsupported road id: {road_id}.")
        elif allowed_road_set and road_id not in allowed_road_set:
            issues.append(f"utterance mentions road outside allowed set: {road_id}.")

    if PASSWORD.lower() in lowered and speech_act != SpeechAct.PROVIDE_PASSWORD:
        issues.append("password can only be spoken during provide_password.")

    issues.extend(validate_speech_act_contract(cleaned, speech_act, mentioned_roads))
    return UtteranceValidationResult(passed=not issues, issues=issues)


# Return whether the utterance has a minimal Polish signal or is the password.
def looks_polish_or_password(utterance: str) -> bool:
    if utterance.strip().lower() == PASSWORD.lower():
        return True
    lowered = utterance.lower()
    return any(signal in lowered for signal in POLISH_SIGNAL_WORDS)


# Validate speech-act-specific requirements.
def validate_speech_act_contract(
    utterance: str,
    speech_act: SpeechAct,
    mentioned_roads: list[str],
) -> list[str]:
    issues: list[str] = []
    lowered = utterance.lower()

    if speech_act == SpeechAct.ASK_ROAD_STATUS:
        if "tymon gajewski" not in lowered:
            issues.append("first road-status request must include the operator identity.")
        missing_roads = sorted(VALID_ROAD_IDS.difference(mentioned_roads))
        if missing_roads:
            issues.append(f"first road-status request misses roads: {', '.join(missing_roads)}.")

    if speech_act == SpeechAct.PROVIDE_PASSWORD and utterance.strip().lower() != PASSWORD.lower():
        issues.append("provide_password utterance must be exactly the operator password.")

    if speech_act == SpeechAct.REQUEST_MONITORING_DISABLE:
        if "monitoring" not in lowered:
            issues.append("monitoring-disable request must mention monitoring.")
        if not mentioned_roads:
            issues.append("monitoring-disable request must mention at least one road.")

    if speech_act == SpeechAct.EXPLAIN_FOOD_TRANSPORT:
        if "zygfryda" not in lowered:
            issues.append("reason explanation must mention Zygfryd's base cover story.")
        if (
            "żywności" not in lowered
            and "zywnosci" not in lowered
            and "jedzenia" not in lowered
            and "jedzenie" not in lowered
        ):
            issues.append("reason explanation must mention food transport.")

    return issues
