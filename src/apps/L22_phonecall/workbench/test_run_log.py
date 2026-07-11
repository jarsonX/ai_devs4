from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.apps.L22_phonecall.config import AppPaths
from src.apps.L22_phonecall.models import (
    ApiResponse,
    AssistantPlan,
    CallReport,
    Confidence,
    ConversationState,
    LoggedExchange,
    OperatorIntent,
    OperatorInterpretation,
    RoadStatus,
    SpeechAct,
    build_road_status_set,
)
from src.apps.L22_phonecall.run_log import CallRunLogger, TranscriptEntry


# Verify that runtime logging writes reviewable text, JSON, and audio artifacts.
class CallRunLoggerTests(unittest.TestCase):
    def test_writes_one_turn_and_masks_request_secret(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app_paths = build_temp_app_paths(Path(temp_dir))
            logger = CallRunLogger(app_paths, call_id="call_test")
            interpretation = OperatorInterpretation(
                intent=OperatorIntent.ROAD_STATUS,
                road_statuses=build_road_status_set({"RD820": RoadStatus.PASSABLE}),
                asks_for_password=False,
                asks_for_reason=False,
                confirms_monitoring_disabled=False,
                mentions_call_failure=False,
                confidence=Confidence.HIGH,
                evidence="RD820 is passable.",
            )
            plan = AssistantPlan(
                speech_act=SpeechAct.REQUEST_MONITORING_DISABLE,
                utterance="Rozumiem. Proszę wyłączyć monitoring na RD820 na czas przejazdu.",
                roads=["RD820"],
                note="test",
            )
            exchange = LoggedExchange(
                sequence=1,
                action="audio",
                request={"apikey": "secret-value", "answer": {"audio": "base64data"}},
                response=ApiResponse(
                    status_code=200,
                    payload={"code": 0, "audio": "responsebase64data"},
                    text='{"audio":"' + ("x" * 1200) + '"}',
                ),
            )

            operator_audio = logger.save_operator_audio(1, b"operator-audio")
            assistant_audio = logger.save_assistant_audio(1, b"assistant-audio")
            logger.save_operator_raw(1, {"message": "ok", "apikey": "secret-value"})
            logger.save_operator_transcript(1, "RD820 jest przejezdna.")
            logger.save_operator_interpretation(1, interpretation)
            logger.save_assistant_plan(1, plan)
            logger.save_assistant_utterance(1, plan.utterance)
            logger.save_hub_request(1, {"apikey": "secret-value", "answer": {"audio": "base64data"}})
            logger.save_hub_response(1, exchange)
            logger.save_call_report(
                CallReport(
                    call_id="call_test",
                    final_state=ConversationState.MONITORING_REQUESTED,
                    flag_found=False,
                    turns=1,
                    hub_requests_used=2,
                    selected_roads=["RD820"],
                )
            )
            logger.save_call_transcript(
                [
                    TranscriptEntry(
                        turn_number=1,
                        operator_text="RD820 jest przejezdna.",
                        assistant_text=plan.utterance,
                        state=ConversationState.MONITORING_REQUESTED.value,
                        operator_audio_path=operator_audio,
                        assistant_audio_path=assistant_audio,
                    )
                ],
                mode="test-mode",
            )

            turn_dir = app_paths.calls_dir / "call_test" / "turn_001"
            self.assertTrue((turn_dir / "operator.raw.json").exists())
            self.assertEqual((turn_dir / "operator.audio.mp3").read_bytes(), b"operator-audio")
            self.assertEqual((turn_dir / "assistant.audio.mp3").read_bytes(), b"assistant-audio")
            request_payload = json.loads((turn_dir / "hub_request.masked.json").read_text(encoding="utf-8"))
            self.assertEqual(request_payload["apikey"], "***REDACTED***")
            self.assertEqual(request_payload["answer"]["audio"]["transport"], "base64_audio")
            self.assertEqual(request_payload["answer"]["audio"]["chars"], len("base64data"))
            response_payload = json.loads((turn_dir / "hub_response.raw.json").read_text(encoding="utf-8"))
            self.assertEqual(response_payload["request"]["apikey"], "***REDACTED***")
            self.assertEqual(response_payload["request"]["answer"]["audio"]["transport"], "base64_audio")
            self.assertEqual(response_payload["response"]["payload"]["audio"]["transport"], "base64_audio")
            self.assertEqual(response_payload["response"]["text"]["transport"], "large_response_text_omitted")
            transcript = (app_paths.calls_dir / "call_test" / "call_transcript.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("operator.audio.mp3", transcript)
            self.assertIn("assistant.audio.mp3", transcript)
            self.assertIn("Mode: `test-mode`", transcript)
            self.assertNotIn("base64data", transcript)

    def test_rebuilds_transcript_from_existing_turn_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app_paths = build_temp_app_paths(Path(temp_dir))
            logger = CallRunLogger(app_paths, call_id="call_test")

            logger.save_operator_transcript(2, "Operator turn two.")
            logger.save_assistant_utterance(2, "Assistant turn two.")
            logger.save_assistant_audio(2, b"assistant-audio-two")
            logger.save_operator_transcript(3, "Operator turn three.")
            logger.save_assistant_utterance(3, "Assistant turn three.")
            logger.save_operator_audio(3, b"operator-audio-three")

            transcript_path = logger.rebuild_call_transcript_from_artifacts(mode="inspect-live-manual")
            transcript = transcript_path.read_text(encoding="utf-8")

            self.assertIn("Mode: `inspect-live-manual`", transcript)
            self.assertIn("## Turn 002", transcript)
            self.assertIn("## Turn 003", transcript)
            self.assertIn("Assistant turn two.", transcript)
            self.assertIn("Operator turn three.", transcript)
            self.assertIn("assistant.audio.mp3", transcript)
            self.assertIn("operator.audio.mp3", transcript)


# Build temporary app paths without touching the real repository data directory.
def build_temp_app_paths(root: Path) -> AppPaths:
    app_dir = root / "src" / "apps" / "L22_phonecall"
    data_dir = root / "data" / "L22_phonecall"
    return AppPaths(
        repo_root=root,
        app_dir=app_dir,
        docs_dir=app_dir / "docs",
        data_dir=data_dir,
        calls_dir=data_dir / "calls",
        output_dir=data_dir / "output",
        logs_dir=data_dir / "logs",
    )


if __name__ == "__main__":
    unittest.main()
