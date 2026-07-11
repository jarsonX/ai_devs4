from __future__ import annotations

import unittest
from typing import Any

from src.apps.L22_phonecall.models import SpeechAct
from src.apps.L22_phonecall.response_planner import ResponsePlanner
from src.apps.L22_phonecall.utterance_guard import validate_utterance


# Return fixed model plans for response-planner boundary tests.
class FakePlannerModel:
    # Store raw outputs and captured requests for assertions.
    def __init__(self, outputs: list[dict[str, Any]]) -> None:
        self.outputs = outputs
        self.requests: list[dict[str, Any]] = []

    # Return the next predefined model proposal.
    def plan(self, request: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(request)
        return self.outputs[len(self.requests) - 1]


# Verify assistant wording is always validated before TTS.
class ResponsePlannerTests(unittest.TestCase):
    def test_status_request_template_is_valid(self) -> None:
        planner = ResponsePlanner()

        plan = planner.plan(SpeechAct.ASK_ROAD_STATUS, max_words=28)
        validation = validate_utterance(plan.utterance, plan.speech_act, max_words=28)

        self.assertTrue(validation.passed, validation.issues)
        self.assertIn("Tymon Gajewski", plan.utterance)
        self.assertIn("RD224", plan.utterance)
        self.assertIn("RD472", plan.utterance)
        self.assertIn("RD820", plan.utterance)

    def test_monitoring_request_uses_selected_roads(self) -> None:
        planner = ResponsePlanner()

        plan = planner.plan(
            SpeechAct.REQUEST_MONITORING_DISABLE,
            roads=["RD820"],
            max_words=28,
        )

        self.assertEqual(plan.roads, ["RD820"])
        self.assertIn("RD820", plan.utterance)
        self.assertNotIn("RD224", plan.utterance)

    def test_model_plan_can_be_used_when_safe(self) -> None:
        model = FakePlannerModel(
            [
                {
                    "speech_act": "request_monitoring_disable",
                    "utterance": "Rozumiem. Prosze wylaczyc monitoring na RD820 na czas przejazdu.",
                    "roads": ["RD820"],
                    "note": "safe fake plan",
                }
            ]
        )
        planner = ResponsePlanner(model_client=model, max_model_requests=1)

        plan = planner.plan(
            SpeechAct.REQUEST_MONITORING_DISABLE,
            roads=["RD820"],
            max_words=28,
            use_model=True,
        )

        self.assertEqual(plan.note, "safe fake plan")
        self.assertEqual(planner.model_requests_used(), 1)
        self.assertEqual(model.requests[0]["speech_act"], "request_monitoring_disable")

    def test_unsafe_model_plan_falls_back_to_template(self) -> None:
        model = FakePlannerModel(
            [
                {
                    "speech_act": "request_monitoring_disable",
                    "utterance": "Trzeba zrobic przerzut ludzi do Syjonu przez RD820.",
                    "roads": ["RD820"],
                    "note": "unsafe fake plan",
                }
            ]
        )
        planner = ResponsePlanner(model_client=model, max_model_requests=1)

        plan = planner.plan(
            SpeechAct.REQUEST_MONITORING_DISABLE,
            roads=["RD820"],
            max_words=28,
            use_model=True,
        )

        self.assertEqual(plan.note, "deterministic_template")
        self.assertNotIn("Syjon", plan.utterance)
        self.assertEqual(planner.model_requests_used(), 1)

    def test_model_guard_stops_before_second_request(self) -> None:
        model = FakePlannerModel(
            [
                {
                    "speech_act": "wait_for_status",
                    "utterance": "Czekam na status drog.",
                    "roads": [],
                    "note": "safe fake plan",
                }
            ]
        )
        planner = ResponsePlanner(model_client=model, max_model_requests=1)

        planner.plan(SpeechAct.WAIT_FOR_STATUS, max_words=28, use_model=True)
        with self.assertRaises(ValueError):
            planner.plan(SpeechAct.WAIT_FOR_STATUS, max_words=28, use_model=True)

        self.assertEqual(len(model.requests), 1)


if __name__ == "__main__":
    unittest.main()
