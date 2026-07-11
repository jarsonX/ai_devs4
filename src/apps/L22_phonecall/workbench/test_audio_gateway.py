from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.apps.L22_phonecall.audio_gateway import AudioGateway


# Return fixed STT and TTS data for audio gateway tests.
class FakeAudioModel:
    # Store generated outputs and captured requests for assertions.
    def __init__(self, *, transcript: str = "RD820 jest przejezdna.", audio_bytes: bytes = b"fake-mp3") -> None:
        self.transcript = transcript
        self.audio_bytes = audio_bytes
        self.transcribe_calls: list[dict[str, object]] = []
        self.synthesize_calls: list[dict[str, object]] = []

    # Return a predefined transcript for one local audio path.
    def transcribe(self, *, audio_path: Path, model: str, language: str) -> str:
        self.transcribe_calls.append(
            {
                "audio_path": audio_path,
                "model": model,
                "language": language,
            }
        )
        return self.transcript

    # Return predefined audio bytes for one approved utterance.
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
        return self.audio_bytes


# Verify STT/TTS file boundaries without real OpenAI calls.
class AudioGatewayTests(unittest.TestCase):
    def make_gateway(self, model: FakeAudioModel, *, max_stt: int = 2, max_tts: int = 2) -> AudioGateway:
        return AudioGateway(
            client=model,
            stt_model="gpt-4o-transcribe",
            tts_model="gpt-4o-mini-tts",
            tts_voice="coral",
            tts_response_format="mp3",
            operator_language="pl",
            max_stt_requests=max_stt,
            max_tts_requests=max_tts,
        )

    def test_transcribes_existing_operator_audio(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "operator.audio.mp3"
            audio_path.write_bytes(b"fake-audio")
            model = FakeAudioModel(transcript="RD820 jest przejezdna.")
            gateway = self.make_gateway(model)

            transcript = gateway.transcribe_operator_audio(audio_path)

            self.assertEqual(transcript, "RD820 jest przejezdna.")
            self.assertEqual(gateway.stt_requests_used(), 1)
            self.assertEqual(model.transcribe_calls[0]["language"], "pl")

    def test_writes_assistant_audio_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "assistant.audio.mp3"
            model = FakeAudioModel(audio_bytes=b"mp3-bytes")
            gateway = self.make_gateway(model)

            written_path = gateway.generate_assistant_audio("Rozumiem. Prosze czekac.", output_path)

            self.assertEqual(written_path, output_path)
            self.assertEqual(output_path.read_bytes(), b"mp3-bytes")
            self.assertEqual(gateway.tts_requests_used(), 1)
            self.assertEqual(model.synthesize_calls[0]["response_format"], "mp3")

    def test_stt_guard_stops_before_second_request(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "operator.audio.mp3"
            audio_path.write_bytes(b"fake-audio")
            model = FakeAudioModel()
            gateway = self.make_gateway(model, max_stt=1)

            gateway.transcribe_operator_audio(audio_path)
            with self.assertRaises(ValueError):
                gateway.transcribe_operator_audio(audio_path)

            self.assertEqual(len(model.transcribe_calls), 1)

    def test_tts_guard_stops_before_second_request(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model = FakeAudioModel()
            gateway = self.make_gateway(model, max_tts=1)

            gateway.generate_assistant_audio("Czekam na status drog.", Path(temp_dir) / "one.mp3")
            with self.assertRaises(ValueError):
                gateway.generate_assistant_audio("Czekam na status drog.", Path(temp_dir) / "two.mp3")

            self.assertEqual(len(model.synthesize_calls), 1)

    def test_rejects_missing_operator_audio_before_request(self) -> None:
        model = FakeAudioModel()
        gateway = self.make_gateway(model)

        with self.assertRaises(ValueError):
            gateway.transcribe_operator_audio(Path("missing.mp3"))

        self.assertEqual(len(model.transcribe_calls), 0)


if __name__ == "__main__":
    unittest.main()
