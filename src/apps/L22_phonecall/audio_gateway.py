# Guarded speech-to-text and text-to-speech boundary for L22 phonecall.

from __future__ import annotations

from pathlib import Path
from typing import Protocol


# Define the minimal audio model surface used by the workflow.
class AudioModelProtocol(Protocol):
    # Transcribe one local operator audio file into text.
    def transcribe(self, *, audio_path: Path, model: str, language: str) -> str:
        ...

    # Generate one audio file payload for an approved assistant utterance.
    def synthesize(
        self,
        *,
        text: str,
        model: str,
        voice: str,
        response_format: str,
    ) -> bytes:
        ...


# Own the request guards and file boundaries for STT and TTS.
class AudioGateway:
    # Store model settings and separate STT/TTS request guards.
    def __init__(
        self,
        *,
        client: AudioModelProtocol,
        stt_model: str,
        tts_model: str,
        tts_voice: str,
        tts_response_format: str,
        operator_language: str,
        max_stt_requests: int,
        max_tts_requests: int,
    ) -> None:
        if max_stt_requests < 0:
            raise ValueError("max_stt_requests must be >= 0.")
        if max_tts_requests < 0:
            raise ValueError("max_tts_requests must be >= 0.")
        self.client = client
        self.stt_model = stt_model
        self.tts_model = tts_model
        self.tts_voice = tts_voice
        self.tts_response_format = tts_response_format
        self.operator_language = operator_language
        self.max_stt_requests = max_stt_requests
        self.max_tts_requests = max_tts_requests
        self._stt_requests_used = 0
        self._tts_requests_used = 0

    # Return how many STT requests were used.
    def stt_requests_used(self) -> int:
        return self._stt_requests_used

    # Return how many TTS requests were used.
    def tts_requests_used(self) -> int:
        return self._tts_requests_used

    # Transcribe one saved operator audio artifact.
    def transcribe_operator_audio(self, audio_path: Path) -> str:
        if not audio_path.is_file():
            raise ValueError(f"Operator audio file does not exist: {audio_path}")
        if self._stt_requests_used >= self.max_stt_requests:
            raise ValueError("The STT request guard was exceeded.")
        self._stt_requests_used += 1

        transcript = self.client.transcribe(
            audio_path=audio_path,
            model=self.stt_model,
            language=self.operator_language,
        ).strip()
        if not transcript:
            raise ValueError("STT returned an empty transcript.")
        return transcript

    # Generate and write assistant audio for one already-approved utterance.
    def generate_assistant_audio(self, utterance: str, output_path: Path) -> Path:
        cleaned = utterance.strip()
        if not cleaned:
            raise ValueError("utterance must not be empty.")
        if self._tts_requests_used >= self.max_tts_requests:
            raise ValueError("The TTS request guard was exceeded.")
        self._tts_requests_used += 1

        audio_bytes = self.client.synthesize(
            text=cleaned,
            model=self.tts_model,
            voice=self.tts_voice,
            response_format=self.tts_response_format,
        )
        if not audio_bytes:
            raise ValueError("TTS returned empty audio bytes.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio_bytes)
        return output_path
