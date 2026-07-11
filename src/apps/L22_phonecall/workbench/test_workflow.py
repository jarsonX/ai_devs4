from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.apps.L22_phonecall.config import AppConfig, AppPaths, RuntimeConfig
from src.apps.L22_phonecall.workflow import (
    build_submit_blocked_result,
    run_dry_run,
    run_local_fixture_workflow,
    run_simulate_audio,
)


# Verify local workflows write useful artifacts without external calls.
class WorkflowTests(unittest.TestCase):
    def test_dry_run_completes_and_writes_review_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_temp_config(Path(temp_dir))

            result = run_dry_run(config)

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["final_state"], "MONITORING_CONFIRMED")
            self.assertEqual(result["selected_roads"], ["RD820"])
            report_path = config.paths.repo_root / str(result["report_path"])
            transcript_path = config.paths.repo_root / str(result["transcript_path"])
            self.assertTrue(report_path.exists())
            self.assertTrue(transcript_path.exists())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["mode"], "dry-run")
            self.assertEqual(report["tts_requests_used"], 0)
            transcript = transcript_path.read_text(encoding="utf-8")
            self.assertIn("Mode: `dry-run`", transcript)
            self.assertIn("assistant.audio.mp3", transcript)

    def test_simulate_audio_counts_stt_and_tts_requests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_temp_config(Path(temp_dir))

            result = run_simulate_audio(config)

            report_path = config.paths.repo_root / str(result["report_path"])
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "completed")
            self.assertEqual(report["mode"], "simulate-audio")
            self.assertEqual(report["stt_requests_used"], 2)
            self.assertEqual(report["tts_requests_used"], 2)
            first_turn = config.paths.repo_root / str(result["call_dir"]) / "turn_001"
            self.assertTrue((first_turn / "operator.audio.mp3").exists())
            self.assertTrue((first_turn / "assistant.audio.mp3").exists())

    def test_submit_mode_is_blocked_without_external_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_temp_config(Path(temp_dir))

            result = build_submit_blocked_result(config)

            self.assertEqual(result["status"], "approval_required")
            self.assertIsNone(result["call_id"])

    def test_password_challenge_scenario_speaks_password_then_continues(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_temp_config(Path(temp_dir))

            result = run_local_fixture_workflow(
                config,
                mode="test",
                transcripts=[
                    "Najpierw podaj haslo operatora.",
                    "RD224 zablokowana, RD472 zamknieta, RD820 przejezdna.",
                    "Monitoring na RD820 wylaczony.",
                ],
                simulate_audio=False,
            )

            self.assertEqual(result.status, "completed")
            turn_one = config.paths.calls_dir / result.call_id / "turn_001" / "assistant.utterance.txt"
            self.assertEqual(turn_one.read_text(encoding="utf-8").lower(), "barbakan")

    def test_reason_challenge_scenario_explains_food_transport(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_temp_config(Path(temp_dir))

            result = run_local_fixture_workflow(
                config,
                mode="test",
                transcripts=[
                    "RD224 zablokowana, RD472 zamknieta, RD820 przejezdna.",
                    "Dlaczego mam wylaczyc monitoring?",
                    "Monitoring na RD820 wylaczony.",
                ],
                simulate_audio=False,
            )

            self.assertEqual(result.status, "completed")
            turn_two = config.paths.calls_dir / result.call_id / "turn_002" / "assistant.utterance.txt"
            self.assertIn("jedzenia", turn_two.read_text(encoding="utf-8"))

    def test_failure_scenario_stops_without_assistant_audio(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_temp_config(Path(temp_dir))

            result = run_local_fixture_workflow(
                config,
                mode="test",
                transcripts=["Rozmowa spalona, uruchamiam alarm."],
                simulate_audio=False,
            )

            self.assertEqual(result.status, "stopped")
            self.assertEqual(result.final_state.value, "FAILED")
            turn_one = config.paths.calls_dir / result.call_id / "turn_001"
            self.assertFalse((turn_one / "assistant.audio.mp3").exists())


# Build temporary app configuration without reading secrets.
def build_temp_config(root: Path) -> AppConfig:
    app_dir = root / "src" / "apps" / "L22_phonecall"
    data_dir = root / "data" / "L22_phonecall"
    paths = AppPaths(
        repo_root=root,
        app_dir=app_dir,
        docs_dir=app_dir / "docs",
        data_dir=data_dir,
        calls_dir=data_dir / "calls",
        output_dir=data_dir / "output",
        logs_dir=data_dir / "logs",
    )
    runtime = RuntimeConfig(
        max_hub_requests=12,
        max_stt_requests=8,
        max_interpreter_requests=10,
        max_planner_requests=8,
        max_tts_requests=8,
        request_timeout_seconds=30,
        max_utterance_words=28,
        operator_language="pl",
    )
    return AppConfig(paths=paths, runtime=runtime, hub=None, openai=None)


if __name__ == "__main__":
    unittest.main()
