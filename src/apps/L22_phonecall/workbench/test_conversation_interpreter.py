from __future__ import annotations

import unittest
from typing import Any

from src.apps.L22_phonecall.conversation_interpreter import ConversationInterpreter, interpret_deterministically
from src.apps.L22_phonecall.models import Confidence, OperatorIntent, RoadStatus


# Return fixed model data for interpreter boundary tests.
class FakeInterpreterModel:
    # Store the raw output and captured calls for assertions.
    def __init__(self, output: dict[str, Any]) -> None:
        self.output = output
        self.calls: list[tuple[str, dict[str, Any]]] = []

    # Return a predefined JSON-like interpretation.
    def interpret(self, transcript: str, context: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((transcript, context))
        return self.output


# Verify transcript interpretation before any real model gateway exists.
class ConversationInterpreterTests(unittest.TestCase):
    def test_extracts_explicit_road_statuses(self) -> None:
        interpretation = interpret_deterministically(
            "RD224 jest zablokowana, RD472 zamknieta przez remont, a RD820 jest przejezdna."
        )

        self.assertEqual(interpretation.intent, OperatorIntent.ROAD_STATUS)
        self.assertEqual(interpretation.road_statuses.statuses["RD224"], RoadStatus.BLOCKED)
        self.assertEqual(interpretation.road_statuses.statuses["RD472"], RoadStatus.BLOCKED)
        self.assertEqual(interpretation.road_statuses.statuses["RD820"], RoadStatus.PASSABLE)
        self.assertEqual(interpretation.confidence, Confidence.HIGH)

    def test_extracts_road_statuses_with_hyphenated_ids(self) -> None:
        interpretation = interpret_deterministically(
            "Droga RD-472 jest nieprzejezdna, podobnie RD-224. Jedynie RD-820 jest przejezdna."
        )

        self.assertEqual(interpretation.intent, OperatorIntent.ROAD_STATUS)
        self.assertEqual(interpretation.road_statuses.statuses["RD224"], RoadStatus.BLOCKED)
        self.assertEqual(interpretation.road_statuses.statuses["RD472"], RoadStatus.BLOCKED)
        self.assertEqual(interpretation.road_statuses.statuses["RD820"], RoadStatus.PASSABLE)

    def test_extracts_only_remaining_road_as_passable(self) -> None:
        interpretation = interpret_deterministically(
            "Droga RD-472 jest nieprzejezdna. Podobnie RD-224. Jedyne co ci zostalo to jechac droga RD-820."
        )

        self.assertEqual(interpretation.road_statuses.statuses["RD224"], RoadStatus.BLOCKED)
        self.assertEqual(interpretation.road_statuses.statuses["RD472"], RoadStatus.BLOCKED)
        self.assertEqual(interpretation.road_statuses.statuses["RD820"], RoadStatus.PASSABLE)

    def test_detects_password_request(self) -> None:
        interpretation = interpret_deterministically("Najpierw podaj haslo operatora.")

        self.assertEqual(interpretation.intent, OperatorIntent.PASSWORD_REQUEST)
        self.assertTrue(interpretation.asks_for_password)
        self.assertEqual(interpretation.confidence, Confidence.HIGH)

    def test_detects_password_request_with_polish_letter(self) -> None:
        interpretation = interpret_deterministically("Jak brzmi hasło?")

        self.assertEqual(interpretation.intent, OperatorIntent.PASSWORD_REQUEST)
        self.assertTrue(interpretation.asks_for_password)

    def test_detects_reason_request(self) -> None:
        interpretation = interpret_deterministically("Dlaczego mam wylaczyc monitoring?")

        self.assertEqual(interpretation.intent, OperatorIntent.REASON_REQUEST)
        self.assertTrue(interpretation.asks_for_reason)

    def test_detects_sprawa_as_reason_request(self) -> None:
        interpretation = interpret_deterministically("W jakiej sprawie dzwonisz?")

        self.assertEqual(interpretation.intent, OperatorIntent.REASON_REQUEST)
        self.assertTrue(interpretation.asks_for_reason)

    def test_detects_monitoring_confirmation(self) -> None:
        interpretation = interpret_deterministically("Monitoring na RD820 wylaczony, mozecie jechac.")

        self.assertEqual(interpretation.intent, OperatorIntent.MONITORING_CONFIRMATION)
        self.assertTrue(interpretation.confirms_monitoring_disabled)

    def test_detects_call_failure(self) -> None:
        interpretation = interpret_deterministically("Rozmowa spalona, uruchamiam alarm.")

        self.assertEqual(interpretation.intent, OperatorIntent.FAILURE)
        self.assertTrue(interpretation.mentions_call_failure)

    def test_does_not_guess_ambiguous_road_references(self) -> None:
        interpretation = interpret_deterministically("Pierwsza odpada, ostatnia jest czysta.")

        self.assertEqual(interpretation.intent, OperatorIntent.OTHER)
        self.assertEqual(interpretation.confidence, Confidence.LOW)
        self.assertEqual(interpretation.road_statuses.statuses["RD224"], RoadStatus.UNKNOWN)
        self.assertEqual(interpretation.road_statuses.statuses["RD472"], RoadStatus.UNKNOWN)
        self.assertEqual(interpretation.road_statuses.statuses["RD820"], RoadStatus.UNKNOWN)

    def test_uses_model_fallback_only_for_low_confidence(self) -> None:
        model = FakeInterpreterModel(
            {
                "intent": "road_status",
                "road_statuses": {"RD820": "passable"},
                "asks_for_password": False,
                "asks_for_reason": False,
                "confirms_monitoring_disabled": False,
                "mentions_call_failure": False,
                "confidence": "medium",
                "evidence": "Fake model resolved the ambiguous reference.",
            }
        )
        interpreter = ConversationInterpreter(model_client=model, max_model_requests=1)

        interpretation = interpreter.interpret("Ostatnia jest czysta.")

        self.assertEqual(interpretation.intent, OperatorIntent.ROAD_STATUS)
        self.assertEqual(interpretation.road_statuses.statuses["RD820"], RoadStatus.PASSABLE)
        self.assertEqual(interpreter.model_requests_used(), 1)
        self.assertEqual(len(model.calls), 1)

    def test_model_guard_stops_before_second_fallback_call(self) -> None:
        model = FakeInterpreterModel(
            {
                "intent": "other",
                "road_statuses": {},
                "asks_for_password": False,
                "asks_for_reason": False,
                "confirms_monitoring_disabled": False,
                "mentions_call_failure": False,
                "confidence": "low",
                "evidence": "Still ambiguous.",
            }
        )
        interpreter = ConversationInterpreter(model_client=model, max_model_requests=1)

        interpreter.interpret("Ostatnia jest czysta.")
        with self.assertRaises(ValueError):
            interpreter.interpret("Pierwsza chyba odpada.")

        self.assertEqual(len(model.calls), 1)


if __name__ == "__main__":
    unittest.main()
