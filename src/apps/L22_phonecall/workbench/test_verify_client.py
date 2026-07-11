from __future__ import annotations

import unittest
from typing import Any

from src.apps.L22_phonecall.config import HubConfig
from src.apps.L22_phonecall.verify_client import PhonecallVerifyClient, build_verify_payload


# Return a fake requests-like response for Hub client tests.
class FakeResponse:
    # Store status, text, and optional JSON payload.
    def __init__(self, status_code: int, text: str, payload: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self.text = text
        self._payload = payload

    # Return JSON or mimic requests when JSON is unavailable.
    def json(self) -> dict[str, Any]:
        if self._payload is None:
            raise ValueError("No JSON payload.")
        return self._payload


# Capture outgoing POST calls without touching the network.
class FakeSession:
    # Store canned responses and captured requests.
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    # Capture one POST and return the next canned response.
    def post(self, *args: Any, **kwargs: Any) -> FakeResponse:
        self.calls.append({"args": args, "kwargs": kwargs})
        return self.responses.pop(0)


# Verify Hub payload construction and request guards without external calls.
class PhonecallVerifyClientTests(unittest.TestCase):
    def test_build_verify_payload_shape(self) -> None:
        config = HubConfig(api_key="secret", verify_url="https://example.test/verify")

        payload = build_verify_payload(config, {"action": "start"})

        self.assertEqual(
            payload,
            {
                "apikey": "secret",
                "task": "phonecall",
                "answer": {"action": "start"},
            },
        )

    def test_start_sends_action_and_masks_logged_request(self) -> None:
        session = FakeSession([FakeResponse(200, "ok", {"code": 0})])
        client = PhonecallVerifyClient(
            HubConfig(api_key="secret", verify_url="https://example.test/verify"),
            timeout_seconds=5,
            max_requests=2,
            session=session,
        )

        exchange = client.start()

        sent_payload = session.calls[0]["kwargs"]["json"]
        self.assertEqual(sent_payload["answer"], {"action": "start"})
        self.assertEqual(exchange.request["apikey"], "***REDACTED***")
        self.assertEqual(exchange.response.payload, {"code": 0})

    def test_send_audio_uses_audio_only_answer(self) -> None:
        session = FakeSession([FakeResponse(200, "ok", {"message": "received"})])
        client = PhonecallVerifyClient(
            HubConfig(api_key="secret", verify_url="https://example.test/verify"),
            timeout_seconds=5,
            max_requests=2,
            session=session,
        )

        exchange = client.send_audio(" abc123 ")

        sent_payload = session.calls[0]["kwargs"]["json"]
        self.assertEqual(sent_payload["answer"], {"audio": "abc123"})
        self.assertNotIn("action", sent_payload["answer"])
        self.assertEqual(exchange.action, "audio")

    def test_empty_audio_is_rejected_before_request(self) -> None:
        session = FakeSession([FakeResponse(200, "ok", {})])
        client = PhonecallVerifyClient(
            HubConfig(api_key="secret", verify_url="https://example.test/verify"),
            timeout_seconds=5,
            max_requests=2,
            session=session,
        )

        with self.assertRaises(ValueError):
            client.send_audio(" ")

        self.assertEqual(session.calls, [])

    def test_guard_exhaustion_stops_before_request(self) -> None:
        session = FakeSession([FakeResponse(200, "ok", {}), FakeResponse(200, "ok", {})])
        client = PhonecallVerifyClient(
            HubConfig(api_key="secret", verify_url="https://example.test/verify"),
            timeout_seconds=5,
            max_requests=1,
            session=session,
        )

        client.start()
        with self.assertRaises(ValueError):
            client.send_audio("abc")

        self.assertEqual(len(session.calls), 1)


if __name__ == "__main__":
    unittest.main()

