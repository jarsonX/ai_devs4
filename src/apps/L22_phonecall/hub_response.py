# Normalize Hub phonecall responses into operator text or audio inputs.

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from typing import Any

from src.apps.L22_phonecall.models import ApiResponse, LoggedExchange


# Store the operator input extracted from one Hub response.
@dataclass(frozen=True)
class OperatorTurnInput:
    text: str | None
    audio_bytes: bytes | None
    audio_extension: str
    source_field: str | None

    # Return whether the response contains audio to transcribe.
    def has_audio(self) -> bool:
        return self.audio_bytes is not None

    # Return whether the response contains text to interpret directly.
    def has_text(self) -> bool:
        return bool(self.text and self.text.strip())


# Extract operator text or audio from a logged Hub exchange.
def extract_operator_turn_input(exchange: LoggedExchange) -> OperatorTurnInput:
    return extract_operator_turn_input_from_response(exchange.response)


# Extract operator text or audio from one normalized API response.
def extract_operator_turn_input_from_response(response: ApiResponse) -> OperatorTurnInput:
    payload = response.payload if isinstance(response.payload, dict) else {}
    audio_from_payload = extract_audio_from_payload(payload)
    if audio_from_payload is not None:
        field_name, audio_bytes, extension = audio_from_payload
        return OperatorTurnInput(
            text=None,
            audio_bytes=audio_bytes,
            audio_extension=extension,
            source_field=field_name,
        )

    text = extract_text_from_payload(payload)
    return OperatorTurnInput(
        text=text,
        audio_bytes=None,
        audio_extension="mp3",
        source_field="msg" if text else None,
    )


# Find a base64-like audio field in a Hub payload.
def extract_audio_from_payload(payload: dict[str, Any]) -> tuple[str, bytes, str] | None:
    for field_name in ("audio", "audio_base64", "msg"):
        value = payload.get(field_name)
        if not isinstance(value, str):
            continue
        decoded = decode_base64_bytes(value)
        if decoded is not None:
            return field_name, decoded, infer_audio_extension(decoded)
    return None


# Extract the most useful text field from a Hub payload.
def extract_text_from_payload(payload: dict[str, Any]) -> str | None:
    for field_name in ("msg", "message"):
        value = payload.get(field_name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


# Decode strict base64 text while rejecting ordinary human messages.
def decode_base64_bytes(value: str) -> bytes | None:
    compact = "".join(value.split())
    if len(compact) < 32:
        return None
    try:
        decoded = base64.b64decode(compact, validate=True)
    except (binascii.Error, ValueError):
        return None
    if len(decoded) < 16:
        return None
    return decoded


# Infer a practical extension for common audio byte signatures.
def infer_audio_extension(audio_bytes: bytes) -> str:
    if audio_bytes.startswith(b"RIFF"):
        return "wav"
    if audio_bytes.startswith(b"ID3") or audio_bytes[:2] == b"\xff\xfb":
        return "mp3"
    if audio_bytes.startswith(b"OggS"):
        return "ogg"
    return "mp3"
