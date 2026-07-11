from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from src.apps.L22_phonecall.config import OpenAIConfig
from src.apps.L22_phonecall.openai_gateway import (
    OpenAIAudioModel,
    OpenAIInterpreterModel,
    OpenAIPlannerModel,
)


# Mimic the binary response object returned by OpenAI speech generation.
class FakeBinaryResponse:
    # Store bytes that the adapter should read.
    def __init__(self, content: bytes) -> None:
        self.content = content

    # Return fake audio bytes through the real SDK-like method.
    def read(self) -> bytes:
        return self.content


# Mimic the OpenAI audio transcriptions resource.
class FakeTranscriptions:
    # Store calls made by the adapter.
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    # Return a fake transcription object.
    def create(self, **kwargs: Any) -> dict[str, str]:
        self.calls.append(kwargs)
        return {"text": "RD820 jest przejezdna."}


# Mimic the OpenAI audio speech resource.
class FakeSpeech:
    # Store calls made by the adapter.
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    # Return fake binary audio response.
    def create(self, **kwargs: Any) -> FakeBinaryResponse:
        self.calls.append(kwargs)
        return FakeBinaryResponse(b"fake-openai-mp3")


# Group fake audio resources like the OpenAI client.
class FakeAudio:
    # Create fake transcription and speech resources.
    def __init__(self) -> None:
        self.transcriptions = FakeTranscriptions()
        self.speech = FakeSpeech()


# Mimic the OpenAI responses resource.
class FakeResponses:
    # Store one output payload and captured create calls.
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    # Return one fake response object with output_text.
    def create(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        return type("FakeResponse", (), {"output_text": json.dumps(self.payload)})()


# Mimic the OpenAI client surface used by the gateway.
class FakeOpenAIClient:
    # Store fake audio and responses resources.
    def __init__(self, response_payload: dict[str, Any] | None = None) -> None:
        self.audio = FakeAudio()
        self.responses = FakeResponses(response_payload or {})


# Verify OpenAI adapter behavior without real API calls.
class OpenAIGatewayTests(unittest.TestCase):
    def test_audio_adapter_transcribes_and_synthesizes_with_configured_models(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "operator.mp3"
            audio_path.write_bytes(b"audio")
            client = FakeOpenAIClient()
            adapter = OpenAIAudioModel(build_openai_config(), client=client)

            transcript = adapter.transcribe(audio_path=audio_path, model="gpt-4o-transcribe", language="pl")
            audio_bytes = adapter.synthesize(
                text="Rozumiem. Prosze czekac.",
                model="gpt-4o-mini-tts",
                voice="coral",
                response_format="mp3",
            )

            self.assertEqual(transcript, "RD820 jest przejezdna.")
            self.assertEqual(audio_bytes, b"fake-openai-mp3")
            self.assertEqual(client.audio.transcriptions.calls[0]["model"], "gpt-4o-transcribe")
            self.assertEqual(client.audio.speech.calls[0]["voice"], "coral")

    def test_interpreter_adapter_returns_validated_dictionary(self) -> None:
        client = FakeOpenAIClient(
            {
                "intent": "road_status",
                "road_statuses": {"RD224": "unknown", "RD472": "unknown", "RD820": "passable"},
                "asks_for_password": False,
                "asks_for_reason": False,
                "confirms_monitoring_disabled": False,
                "mentions_call_failure": False,
                "confidence": "high",
                "evidence": "Operator explicitly said RD820 is passable.",
            }
        )
        adapter = OpenAIInterpreterModel(build_openai_config(), client=client)

        payload = adapter.interpret("RD820 jest przejezdna.", {"irrelevant": "dropped"})

        self.assertEqual(payload["intent"], "road_status")
        self.assertEqual(payload["road_statuses"]["RD820"], "passable")
        self.assertEqual(client.responses.calls[0]["model"], "gpt-5-mini")
        self.assertEqual(client.responses.calls[0]["text"]["format"]["strict"], True)
        self.assertNotIn("propertyNames", json.dumps(client.responses.calls[0]["text"]["format"]["schema"]))

    def test_planner_adapter_returns_validated_dictionary(self) -> None:
        client = FakeOpenAIClient(
            {
                "speech_act": "request_monitoring_disable",
                "utterance": "Rozumiem. Prosze wylaczyc monitoring na RD820 na czas przejazdu.",
                "roads": ["RD820"],
                "note": "Safe concise request.",
            }
        )
        adapter = OpenAIPlannerModel(build_openai_config(), client=client)

        payload = adapter.plan(
            {
                "speech_act": "request_monitoring_disable",
                "roads": ["RD820"],
                "max_words": 28,
            }
        )

        self.assertEqual(payload["speech_act"], "request_monitoring_disable")
        self.assertEqual(payload["roads"], ["RD820"])
        self.assertEqual(client.responses.calls[0]["text"]["format"]["name"], "l22_phonecall_assistant_plan")

    def test_invalid_structured_output_is_rejected(self) -> None:
        client = FakeOpenAIClient({"intent": "road_status"})
        adapter = OpenAIInterpreterModel(build_openai_config(), client=client)

        with self.assertRaises(ValueError):
            adapter.interpret("RD820 jest przejezdna.", {})


# Build non-secret OpenAI config for adapter tests.
def build_openai_config() -> OpenAIConfig:
    return OpenAIConfig(
        api_key="test-key",
        stt_model="gpt-4o-transcribe",
        interpreter_model="gpt-5-mini",
        planner_model="gpt-5-mini",
        tts_model="gpt-4o-mini-tts",
        tts_voice="coral",
        tts_response_format="mp3",
    )


if __name__ == "__main__":
    unittest.main()
