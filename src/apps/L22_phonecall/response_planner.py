# Build guarded assistant utterances for approved speech acts.

from __future__ import annotations

from typing import Any, Protocol

from src.apps.L22_phonecall.models import AssistantPlan, SpeechAct, VALID_ROAD_IDS
from src.apps.L22_phonecall.state_machine import PASSWORD
from src.apps.L22_phonecall.utterance_guard import validate_utterance


# Define the small model boundary used only for optional wording.
class PlannerModelProtocol(Protocol):
    # Return one JSON-like plan proposal for a pre-approved speech act.
    def plan(self, request: dict[str, Any]) -> dict[str, Any]:
        ...


# Produce assistant plans and reject unsafe model wording.
class ResponsePlanner:
    # Store the optional model client and request guard for wording calls.
    def __init__(
        self,
        *,
        model_client: PlannerModelProtocol | None = None,
        max_model_requests: int = 0,
    ) -> None:
        if max_model_requests < 0:
            raise ValueError("max_model_requests must be >= 0.")
        self.model_client = model_client
        self.max_model_requests = max_model_requests
        self._model_requests_used = 0

    # Return how many planner model requests have been used.
    def model_requests_used(self) -> int:
        return self._model_requests_used

    # Build one safe assistant plan for a speech act chosen by the state machine.
    def plan(
        self,
        speech_act: SpeechAct,
        *,
        roads: list[str] | tuple[str, ...] = (),
        max_words: int,
        use_model: bool = False,
    ) -> AssistantPlan:
        normalized_roads = normalize_roads(roads)
        if use_model and self.model_client is not None:
            model_plan = self._try_model_plan(speech_act, roads=normalized_roads, max_words=max_words)
            if model_plan is not None:
                return model_plan
        return build_valid_template_plan(speech_act, roads=normalized_roads, max_words=max_words)

    # Ask the optional model for wording and return None when the guard rejects it.
    def _try_model_plan(
        self,
        speech_act: SpeechAct,
        *,
        roads: tuple[str, ...],
        max_words: int,
    ) -> AssistantPlan | None:
        if self._model_requests_used >= self.max_model_requests:
            raise ValueError("The planner request guard was exceeded.")
        self._model_requests_used += 1

        raw_output = self.model_client.plan(
            {
                "speech_act": speech_act.value,
                "roads": list(roads),
                "max_words": max_words,
            }
        )
        candidate = parse_model_plan(raw_output, expected_speech_act=speech_act, default_roads=roads)
        validation = validate_utterance(
            candidate.utterance,
            candidate.speech_act,
            allowed_roads=candidate.roads,
            max_words=max_words,
        )
        if validation.passed:
            return candidate
        return None


# Normalize and validate selected roads before they reach wording code.
def normalize_roads(roads: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(sorted(dict.fromkeys(roads)))
    for road_id in normalized:
        if road_id not in VALID_ROAD_IDS:
            raise ValueError(f"Unsupported road id: {road_id}")
    return normalized


# Build one deterministic plan and fail if the local template violates the guard.
def build_valid_template_plan(
    speech_act: SpeechAct,
    *,
    roads: tuple[str, ...],
    max_words: int,
) -> AssistantPlan:
    plan = build_template_plan(speech_act, roads=roads)
    validation = validate_utterance(
        plan.utterance,
        plan.speech_act,
        allowed_roads=plan.roads,
        max_words=max_words,
    )
    if not validation.passed:
        joined = "; ".join(validation.issues)
        raise ValueError(f"Template utterance failed validation: {joined}")
    return plan


# Build deterministic utterances for constrained phone-call speech acts.
def build_template_plan(speech_act: SpeechAct, *, roads: tuple[str, ...]) -> AssistantPlan:
    if speech_act == SpeechAct.ASK_ROAD_STATUS:
        utterance = (
            "Dzien dobry, nazywam sie Tymon Gajewski, Tymon przez litere T. Potrzebuje statusu drog RD224, RD472 i RD820 "
            "dla transportu do bazy Zygfryda."
        )
        plan_roads = sorted(VALID_ROAD_IDS)
    elif speech_act == SpeechAct.PROVIDE_PASSWORD:
        utterance = PASSWORD.lower()
        plan_roads = []
    elif speech_act == SpeechAct.REQUEST_MONITORING_DISABLE:
        if not roads:
            raise ValueError("Monitoring request requires at least one road.")
        utterance = (
            f"Prosze wylaczyc monitoring na {', '.join(roads)}. "
            "To tajna operacja zlecona przez Zygfryda, przejazd musi byc niewidoczny."
        )
        plan_roads = list(roads)
    elif speech_act == SpeechAct.EXPLAIN_FOOD_TRANSPORT:
        utterance = "To tajny transport jedzenia dla Zygfryda. Musze znalezc przejezdna droge do jego bazy."
        plan_roads = list(roads)
    elif speech_act == SpeechAct.CLARIFY_STATUS:
        utterance = "Potwierdz prosze, ktore z drog RD224, RD472 i RD820 sa przejezdne."
        plan_roads = sorted(VALID_ROAD_IDS)
    elif speech_act == SpeechAct.CLARIFY_MONITORING:
        utterance = "Potwierdz prosze, czy monitoring na wskazanej drodze zostal wylaczony."
        plan_roads = list(roads)
    elif speech_act == SpeechAct.WAIT_FOR_STATUS:
        utterance = "Czekam na status drog."
        plan_roads = []
    elif speech_act == SpeechAct.WAIT_FOR_CONFIRMATION:
        utterance = "Czekam na potwierdzenie wylaczenia monitoringu."
        plan_roads = list(roads)
    elif speech_act == SpeechAct.FINISH:
        utterance = "Przyjalem, dziekuje."
        plan_roads = []
    else:
        raise ValueError(f"No template utterance for speech act: {speech_act.value}")
    return AssistantPlan(
        speech_act=speech_act,
        utterance=utterance,
        roads=plan_roads,
        note="deterministic_template",
    )


# Validate one JSON-like model plan before the guard checks its utterance.
def parse_model_plan(
    raw_output: dict[str, Any],
    *,
    expected_speech_act: SpeechAct,
    default_roads: tuple[str, ...],
) -> AssistantPlan:
    if not isinstance(raw_output, dict):
        raise ValueError("Planner model output must be a dictionary.")
    raw_speech_act = str(raw_output.get("speech_act", expected_speech_act.value))
    speech_act = SpeechAct(raw_speech_act)
    if speech_act != expected_speech_act:
        raise ValueError("Planner model returned a different speech act.")
    utterance = raw_output.get("utterance")
    if not isinstance(utterance, str):
        raise ValueError("Planner model output must include utterance as a string.")
    raw_roads = raw_output.get("roads", list(default_roads))
    if not isinstance(raw_roads, list):
        raise ValueError("Planner model roads must be a list.")
    roads = list(normalize_roads([str(road_id) for road_id in raw_roads]))
    note = str(raw_output.get("note", "model_plan"))
    return AssistantPlan(
        speech_act=speech_act,
        utterance=utterance,
        roads=roads,
        note=note,
    )
