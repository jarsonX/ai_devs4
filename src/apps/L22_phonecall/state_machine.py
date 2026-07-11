# Deterministic state transitions for the L22 phonecall conversation.

from __future__ import annotations

from dataclasses import dataclass, field

from src.apps.L22_phonecall.models import (
    AssistantPlan,
    Confidence,
    ConversationState,
    OperatorIntent,
    OperatorInterpretation,
    RoadStatus,
    RoadStatusSet,
    SpeechAct,
    VALID_ROAD_IDS,
)


IDENTITY = "Tymon Gajewski"
PASSWORD = "BARBAKAN"


# Store the conversation state that code, not the model, is allowed to mutate.
@dataclass(frozen=True)
class ConversationSnapshot:
    state: ConversationState = ConversationState.NEW
    road_statuses: RoadStatusSet = field(default_factory=RoadStatusSet)
    selected_roads: tuple[str, ...] = ()
    last_error: str | None = None

    # Return a copy with selected fields changed.
    def replace(
        self,
        *,
        state: ConversationState | None = None,
        road_statuses: RoadStatusSet | None = None,
        selected_roads: tuple[str, ...] | None = None,
        last_error: str | None = None,
    ) -> "ConversationSnapshot":
        return ConversationSnapshot(
            state=state or self.state,
            road_statuses=road_statuses or self.road_statuses,
            selected_roads=selected_roads if selected_roads is not None else self.selected_roads,
            last_error=last_error,
        )


# Store one transition result for logging and planner input.
@dataclass(frozen=True)
class StateDecision:
    snapshot: ConversationSnapshot
    speech_act: SpeechAct
    reason: str


# Move from a new local state to the post-Hub-start state.
def mark_session_started(snapshot: ConversationSnapshot) -> StateDecision:
    if snapshot.state != ConversationState.NEW:
        return StateDecision(
            snapshot=snapshot.replace(
                state=ConversationState.FAILED,
                last_error="Hub session can only start from NEW.",
            ),
            speech_act=SpeechAct.RESTART_SESSION,
            reason="session_start_from_invalid_state",
        )
    updated = snapshot.replace(state=ConversationState.STARTED)
    return StateDecision(
        snapshot=updated,
        speech_act=SpeechAct.ASK_ROAD_STATUS,
        reason="hub_session_started",
    )


# Mark that one assistant speech act has been sent to the operator.
def mark_speech_act_sent(snapshot: ConversationSnapshot, speech_act: SpeechAct) -> ConversationSnapshot:
    if speech_act == SpeechAct.ASK_ROAD_STATUS:
        return snapshot.replace(state=ConversationState.ASKED_ROAD_STATUS)
    if speech_act == SpeechAct.PROVIDE_PASSWORD:
        return snapshot.replace(state=ConversationState.ASKED_ROAD_STATUS)
    if speech_act == SpeechAct.REQUEST_MONITORING_DISABLE:
        return snapshot.replace(state=ConversationState.MONITORING_REQUESTED)
    if speech_act == SpeechAct.EXPLAIN_FOOD_TRANSPORT:
        return snapshot.replace(state=ConversationState.MONITORING_REQUESTED)
    return snapshot


# Apply validated operator interpretation and choose the next legal speech act.
def apply_operator_interpretation(
    snapshot: ConversationSnapshot,
    interpretation: OperatorInterpretation,
) -> StateDecision:
    if interpretation.mentions_call_failure or interpretation.intent == OperatorIntent.FAILURE:
        failed = snapshot.replace(
            state=ConversationState.FAILED,
            last_error="Operator indicated the call failed.",
        )
        return StateDecision(failed, SpeechAct.RESTART_SESSION, "operator_failure")

    if interpretation.confirms_monitoring_disabled:
        confirmed = snapshot.replace(state=ConversationState.MONITORING_CONFIRMED)
        return StateDecision(confirmed, SpeechAct.FINISH, "monitoring_confirmed")

    if interpretation.asks_for_password:
        challenged = snapshot.replace(state=ConversationState.AUTH_CHALLENGE)
        return StateDecision(challenged, SpeechAct.PROVIDE_PASSWORD, "password_requested")

    if interpretation.asks_for_reason:
        challenged = snapshot.replace(state=ConversationState.REASON_CHALLENGE)
        return StateDecision(challenged, SpeechAct.EXPLAIN_FOOD_TRANSPORT, "reason_requested")

    merged_statuses = merge_road_statuses(snapshot.road_statuses, interpretation.road_statuses)
    passable_roads = tuple(road_id for road_id in merged_statuses.passable_roads())
    if passable_roads and interpretation.confidence in {Confidence.HIGH, Confidence.MEDIUM}:
        updated = snapshot.replace(
            state=ConversationState.ROAD_STATUS_KNOWN,
            road_statuses=merged_statuses,
            selected_roads=passable_roads,
        )
        return StateDecision(
            updated,
            SpeechAct.REQUEST_MONITORING_DISABLE,
            "passable_roads_known",
        )

    if all(status != RoadStatus.UNKNOWN for status in merged_statuses.statuses.values()):
        failed = snapshot.replace(
            state=ConversationState.FAILED,
            road_statuses=merged_statuses,
            last_error="No passable road was reported.",
        )
        return StateDecision(failed, SpeechAct.RESTART_SESSION, "no_passable_roads")

    updated = snapshot.replace(
        state=ConversationState.ASKED_ROAD_STATUS,
        road_statuses=merged_statuses,
    )
    return StateDecision(updated, SpeechAct.CLARIFY_STATUS, "road_status_unclear")


# Merge new non-unknown road statuses into the current known state.
def merge_road_statuses(current: RoadStatusSet, new_statuses: RoadStatusSet) -> RoadStatusSet:
    merged = dict(current.statuses)
    for road_id in sorted(VALID_ROAD_IDS):
        status = new_statuses.statuses.get(road_id, RoadStatus.UNKNOWN)
        if status != RoadStatus.UNKNOWN:
            merged[road_id] = status
    return RoadStatusSet(statuses=merged)


# Build the deterministic fallback plan for a speech act.
def build_fallback_plan(
    speech_act: SpeechAct,
    *,
    roads: list[str] | tuple[str, ...] = (),
) -> AssistantPlan:
    normalized_roads = tuple(sorted(roads))
    if speech_act == SpeechAct.ASK_ROAD_STATUS:
        utterance = (
            "Dzien dobry, nazywam sie Tymon Gajewski, Tymon przez litere T. Potrzebuje statusu drog RD224, RD472 i RD820 "
            "dla transportu do bazy Zygfryda."
        )
    elif speech_act == SpeechAct.PROVIDE_PASSWORD:
        utterance = PASSWORD.lower()
    elif speech_act == SpeechAct.REQUEST_MONITORING_DISABLE:
        if not normalized_roads:
            raise ValueError("Monitoring request requires at least one road.")
        road_list = ", ".join(normalized_roads)
        utterance = (
            f"Prosze wylaczyc monitoring na {road_list}. "
            "To tajna operacja zlecona przez Zygfryda, przejazd musi byc niewidoczny."
        )
    elif speech_act == SpeechAct.EXPLAIN_FOOD_TRANSPORT:
        utterance = "To tajny transport jedzenia dla Zygfryda. Musze znalezc przejezdna droge do jego bazy."
    elif speech_act == SpeechAct.CLARIFY_STATUS:
        utterance = "Potwierdź proszę, które z dróg RD224, RD472 i RD820 są przejezdne."
    elif speech_act == SpeechAct.CLARIFY_MONITORING:
        utterance = "Potwierdź proszę, czy monitoring na wskazanej drodze został wyłączony."
    elif speech_act == SpeechAct.WAIT_FOR_STATUS:
        utterance = "Czekam na status dróg."
    elif speech_act == SpeechAct.WAIT_FOR_CONFIRMATION:
        utterance = "Czekam na potwierdzenie wyłączenia monitoringu."
    elif speech_act == SpeechAct.FINISH:
        utterance = "Przyjąłem, dziękuję."
    else:
        raise ValueError(f"No fallback utterance for speech act: {speech_act.value}")
    return AssistantPlan(
        speech_act=speech_act,
        utterance=utterance,
        roads=list(normalized_roads),
        note="deterministic_fallback",
    )
