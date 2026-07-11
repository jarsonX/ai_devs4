from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

import base64

from src.apps.L22_phonecall.config import AppConfig, AppPaths, HubConfig, RuntimeConfig
from src.apps.L22_phonecall.models import SpeechAct
from src.apps.L22_phonecall.live_inspection import (
    inspect_live_first_audio_turn,
    inspect_live_start,
    send_live_speech_act,
    transcribe_saved_operator_audio,
)


# Return fixed HTTP-like responses for live inspection tests.
class FakeResponse:
    # Store fake status and payload values.
    def __init__(self, payload: dict[str, Any]) -> None:
        self.status_code = 200
        self._payload = payload
        self.text = json.dumps(payload)

    # Return the fake JSON payload.
    def json(self) -> dict[str, Any]:
        return self._payload


# Capture one fake Hub POST call.
class FakeSession:
    # Store captured requests for assertions.
    def __init__(self, responses: list[dict[str, Any]] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.responses = responses or [{"message": "started", "audio": "base64-audio"}]

    # Return a fake start response.
    def post(self, url: str, *, json: dict[str, Any], timeout: int) -> FakeResponse:
        self.calls.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse(self.responses.pop(0))


# Return fixed TTS bytes for first-turn inspection tests.
class FakeAudioModel:
    # Store captured synthesize calls.
    def __init__(self) -> None:
        self.synthesize_calls: list[dict[str, Any]] = []
        self.transcribe_calls: list[dict[str, Any]] = []

    # Return a fixed transcript for saved operator audio.
    def transcribe(self, *, audio_path: Path, model: str, language: str) -> str:
        self.transcribe_calls.append(
            {
                "audio_path": audio_path,
                "model": model,
                "language": language,
            }
        )
        return "RD224 zablokowana, RD472 zamknieta, RD820 przejezdna."

    # Return fake assistant MP3 bytes.
    def synthesize(
        self,
        *,
        text: str,
        model: str,
        voice: str,
        response_format: str,
    ) -> bytes:
        self.synthesize_calls.append(
            {
                "text": text,
                "model": model,
                "voice": voice,
                "response_format": response_format,
            }
        )
        return b"ID3" + b"assistant-audio"


# Verify live inspection plumbing without external calls.
class LiveInspectionTests(unittest.TestCase):
    def test_live_start_inspection_writes_masked_runtime_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_temp_config(Path(temp_dir))
            session = FakeSession()

            result = inspect_live_start(config, session=session)

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["hub_requests_used"], 1)
            self.assertEqual(result["response_keys"], ["audio", "message"])
            self.assertEqual(session.calls[0]["json"]["answer"], {"action": "start"})
            turn_dir = config.paths.repo_root / str(result["call_dir"]) / "turn_001"
            request_payload = json.loads((turn_dir / "hub_request.masked.json").read_text(encoding="utf-8"))
            self.assertEqual(request_payload["apikey"], "***REDACTED***")
            self.assertTrue((turn_dir / "hub_response.raw.json").exists())

    def test_first_audio_turn_inspection_sends_audio_and_saves_operator_audio(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_temp_config(Path(temp_dir))
            operator_audio = b"ID3" + b"operator-audio" * 4
            session = FakeSession(
                [
                    {"message": "started", "msg": "session ready"},
                    {"message": "operator reply", "msg": base64.b64encode(operator_audio).decode("ascii")},
                ]
            )
            audio_model = FakeAudioModel()

            result = inspect_live_first_audio_turn(config, session=session, audio_model=audio_model)

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["hub_requests_used"], 2)
            self.assertEqual(result["operator_input_kind"], "audio")
            self.assertEqual(len(session.calls), 2)
            self.assertEqual(session.calls[1]["json"]["answer"].keys(), {"audio"})
            turn_two = config.paths.repo_root / str(result["call_dir"]) / "turn_002"
            self.assertTrue((turn_two / "assistant.audio.mp3").exists())
            self.assertTrue((turn_two / "operator.audio.mp3").exists())
            request_payload = json.loads((turn_two / "hub_request.masked.json").read_text(encoding="utf-8"))
            self.assertEqual(request_payload["answer"]["audio"]["transport"], "base64_audio")
            self.assertEqual(audio_model.synthesize_calls[0]["response_format"], "mp3")

    def test_transcribes_saved_operator_audio_and_writes_interpretation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_temp_config(Path(temp_dir))
            call_id = "call_test"
            turn_dir = config.paths.calls_dir / call_id / "turn_002"
            turn_dir.mkdir(parents=True, exist_ok=True)
            (turn_dir / "operator.audio.mp3").write_bytes(b"ID3operator-audio")
            audio_model = FakeAudioModel()

            result = transcribe_saved_operator_audio(
                config,
                call_id=call_id,
                turn_number=2,
                audio_model=audio_model,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["intent"], "road_status")
            self.assertEqual(result["road_statuses"]["RD820"], "passable")
            self.assertTrue((turn_dir / "operator.transcript.txt").exists())
            self.assertTrue((turn_dir / "operator.interpretation.json").exists())
            self.assertEqual(len(audio_model.transcribe_calls), 1)

    def test_send_live_speech_act_writes_audio_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_temp_config(Path(temp_dir))
            call_id = "call_test"
            previous_turn = config.paths.calls_dir / call_id / "turn_002"
            previous_turn.mkdir(parents=True, exist_ok=True)
            (previous_turn / "operator.transcript.txt").write_text("Previous operator.", encoding="utf-8")
            (previous_turn / "assistant.utterance.txt").write_text("Previous assistant.", encoding="utf-8")
            operator_audio = b"ID3" + b"operator-audio" * 4
            session = FakeSession(
                [
                    {"message": "operator reply", "audio": base64.b64encode(operator_audio).decode("ascii")},
                ]
            )
            audio_model = FakeAudioModel()

            result = send_live_speech_act(
                config,
                call_id=call_id,
                turn_number=3,
                speech_act=SpeechAct.EXPLAIN_FOOD_TRANSPORT,
                session=session,
                audio_model=audio_model,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["operator_input_kind"], "audio")
            self.assertEqual(session.calls[0]["json"]["answer"].keys(), {"audio"})
            turn_three = config.paths.calls_dir / call_id / "turn_003"
            self.assertTrue((turn_three / "assistant.audio.mp3").exists())
            self.assertTrue((turn_three / "operator.audio.mp3").exists())
            transcript = (config.paths.calls_dir / call_id / "call_transcript.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Mode: `inspect-live-manual`", transcript)
            self.assertIn("Previous operator.", transcript)
            self.assertIn("## Turn 003", transcript)
            request_payload = json.loads((turn_three / "hub_request.masked.json").read_text(encoding="utf-8"))
            self.assertEqual(request_payload["answer"]["audio"]["transport"], "base64_audio")


# Build temporary app configuration with fake Hub config.
def build_temp_config(root: Path) -> AppConfig:
    app_dir = root / "src" / "apps" / "L22_phonecall"
    data_dir = root / "data" / "L22_phonecall"
    return AppConfig(
        paths=AppPaths(
            repo_root=root,
            app_dir=app_dir,
            docs_dir=app_dir / "docs",
            data_dir=data_dir,
            calls_dir=data_dir / "calls",
            output_dir=data_dir / "output",
            logs_dir=data_dir / "logs",
        ),
        runtime=RuntimeConfig(
            max_hub_requests=12,
            max_stt_requests=8,
            max_interpreter_requests=10,
            max_planner_requests=8,
            max_tts_requests=8,
            request_timeout_seconds=30,
            max_utterance_words=28,
            operator_language="pl",
        ),
        hub=HubConfig(api_key="secret-key", verify_url="https://example.invalid/verify"),
        openai=None,
    )


if __name__ == "__main__":
    unittest.main()
