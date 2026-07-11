from __future__ import annotations

import unittest

from src.apps.L22_phonecall.models import (
    Confidence,
    ConversationState,
    OperatorIntent,
    OperatorInterpretation,
    RoadStatus,
    SpeechAct,
    build_road_status_set,
)
from src.apps.L22_phonecall.state_machine import (
    ConversationSnapshot,
    build_fallback_plan,
    apply_operator_interpretation,
    mark_session_started,
    mark_speech_act_sent,
)
from src.apps.L22_phonecall.utterance_guard import validate_utterance


# Verify deterministic conversation transitions independent of model calls.
class StateMachineTests(unittest.TestCase):
    def test_normal_path_reaches_monitoring_request(self) -> None:
        decision = mark_session_started(ConversationSnapshot())
        self.assertEqual(decision.speech_act, SpeechAct.ASK_ROAD_STATUS)
        asked = mark_speech_act_sent(decision.snapshot, decision.speech_act)
        interpretation = OperatorInterpretation(
            intent=OperatorIntent.ROAD_STATUS,
            road_statuses=build_road_status_set(
                {
                    "RD224": RoadStatus.BLOCKED,
                    "RD472": RoadStatus.UNKNOWN,
                    "RD820": RoadStatus.PASSABLE,
                }
            ),
            asks_for_password=False,
            asks_for_reason=False,
            confirms_monitoring_disabled=False,
            mentions_call_failure=False,
            confidence=Confidence.HIGH,
            evidence="RD820 is clear.",
        )

        result = apply_operator_interpretation(asked, interpretation)

        self.assertEqual(result.snapshot.state, ConversationState.ROAD_STATUS_KNOWN)
        self.assertEqual(result.speech_act, SpeechAct.REQUEST_MONITORING_DISABLE)
        self.assertEqual(result.snapshot.selected_roads, ("RD820",))

    def test_password_challenge_is_handled_before_status(self) -> None:
        snapshot = ConversationSnapshot(state=ConversationState.ASKED_ROAD_STATUS)
        interpretation = OperatorInterpretation(
            intent=OperatorIntent.PASSWORD_REQUEST,
            road_statuses=build_road_status_set({}),
            asks_for_password=True,
            asks_for_reason=False,
            confirms_monitoring_disabled=False,
            mentions_call_failure=False,
            confidence=Confidence.HIGH,
            evidence="Operator requested password.",
        )

        result = apply_operator_interpretation(snapshot, interpretation)

        self.assertEqual(result.snapshot.state, ConversationState.AUTH_CHALLENGE)
        self.assertEqual(result.speech_act, SpeechAct.PROVIDE_PASSWORD)

    def test_reason_challenge_is_handled_after_monitoring_request(self) -> None:
        snapshot = ConversationSnapshot(
            state=ConversationState.MONITORING_REQUESTED,
            selected_roads=("RD820",),
        )
        interpretation = OperatorInterpretation(
            intent=OperatorIntent.REASON_REQUEST,
            road_statuses=build_road_status_set({}),
            asks_for_password=False,
            asks_for_reason=True,
            confirms_monitoring_disabled=False,
            mentions_call_failure=False,
            confidence=Confidence.HIGH,
            evidence="Operator asked why.",
        )

        result = apply_operator_interpretation(snapshot, interpretation)

        self.assertEqual(result.snapshot.state, ConversationState.REASON_CHALLENGE)
        self.assertEqual(result.speech_act, SpeechAct.EXPLAIN_FOOD_TRANSPORT)

    def test_multiple_passable_roads_are_selected(self) -> None:
        snapshot = ConversationSnapshot(state=ConversationState.ASKED_ROAD_STATUS)
        interpretation = OperatorInterpretation(
            intent=OperatorIntent.ROAD_STATUS,
            road_statuses=build_road_status_set(
                {
                    "RD224": RoadStatus.PASSABLE,
                    "RD472": RoadStatus.BLOCKED,
                    "RD820": RoadStatus.PASSABLE,
                }
            ),
            asks_for_password=False,
            asks_for_reason=False,
            confirms_monitoring_disabled=False,
            mentions_call_failure=False,
            confidence=Confidence.HIGH,
            evidence="Two routes are clear.",
        )

        result = apply_operator_interpretation(snapshot, interpretation)

        self.assertEqual(result.snapshot.selected_roads, ("RD224", "RD820"))
        self.assertEqual(result.speech_act, SpeechAct.REQUEST_MONITORING_DISABLE)

    def test_no_passable_roads_fails_safely(self) -> None:
        snapshot = ConversationSnapshot(state=ConversationState.ASKED_ROAD_STATUS)
        interpretation = OperatorInterpretation(
            intent=OperatorIntent.ROAD_STATUS,
            road_statuses=build_road_status_set(
                {
                    "RD224": RoadStatus.BLOCKED,
                    "RD472": RoadStatus.BLOCKED,
                    "RD820": RoadStatus.BLOCKED,
                }
            ),
            asks_for_password=False,
            asks_for_reason=False,
            confirms_monitoring_disabled=False,
            mentions_call_failure=False,
            confidence=Confidence.HIGH,
            evidence="All roads blocked.",
        )

        result = apply_operator_interpretation(snapshot, interpretation)

        self.assertEqual(result.snapshot.state, ConversationState.FAILED)
        self.assertEqual(result.speech_act, SpeechAct.RESTART_SESSION)


# Verify the assistant cannot speak unsafe or out-of-order content.
class UtteranceGuardTests(unittest.TestCase):
    def test_first_status_request_fallback_is_valid(self) -> None:
        plan = build_fallback_plan(SpeechAct.ASK_ROAD_STATUS)

        result = validate_utterance(
            plan.utterance,
            plan.speech_act,
            max_words=28,
        )

        self.assertTrue(result.passed, result.issues)

    def test_password_fallback_is_valid_only_for_password_act(self) -> None:
        plan = build_fallback_plan(SpeechAct.PROVIDE_PASSWORD)

        valid = validate_utterance(plan.utterance, plan.speech_act, max_words=28)
        invalid = validate_utterance(plan.utterance, SpeechAct.ASK_ROAD_STATUS, max_words=28)

        self.assertTrue(valid.passed, valid.issues)
        self.assertFalse(invalid.passed)

    def test_monitoring_request_requires_allowed_road(self) -> None:
        plan = build_fallback_plan(SpeechAct.REQUEST_MONITORING_DISABLE, roads=["RD820"])

        valid = validate_utterance(
            plan.utterance,
            plan.speech_act,
            allowed_roads=["RD820"],
            max_words=28,
        )
        invalid = validate_utterance(
            plan.utterance,
            plan.speech_act,
            allowed_roads=["RD224"],
            max_words=28,
        )

        self.assertTrue(valid.passed, valid.issues)
        self.assertFalse(invalid.passed)

    def test_forbidden_true_objective_terms_are_blocked(self) -> None:
        result = validate_utterance(
            "Musimy zrobić przerzut ludzi do Syjonu przez RD820.",
            SpeechAct.REQUEST_MONITORING_DISABLE,
            allowed_roads=["RD820"],
            max_words=28,
        )

        self.assertFalse(result.passed)
        self.assertTrue(any("forbidden" in issue for issue in result.issues))

    def test_premature_monitoring_request_without_road_is_blocked(self) -> None:
        result = validate_utterance(
            "Proszę wyłączyć monitoring na czas przejazdu.",
            SpeechAct.REQUEST_MONITORING_DISABLE,
            max_words=28,
        )

        self.assertFalse(result.passed)
        self.assertTrue(any("road" in issue for issue in result.issues))


if __name__ == "__main__":
    unittest.main()

