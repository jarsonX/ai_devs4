# Runtime artifact writer for L22 phonecall attempts.

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.apps.L22_phonecall.config import AppPaths
from src.apps.L22_phonecall.models import (
    AssistantPlan,
    CallReport,
    LoggedExchange,
    OperatorInterpretation,
)


REDACTED = "***REDACTED***"
SECRET_FIELD_NAMES = frozenset({"apikey", "api_key", "authorization", "openai_api_key"})
AUDIO_FIELD_NAMES = frozenset({"audio", "audio_base64"})


# Store paths for one call run.
@dataclass(frozen=True)
class CallRunPaths:
    call_id: str
    call_dir: Path
    report_path: Path
    transcript_path: Path


# Store paths for one call turn.
@dataclass(frozen=True)
class TurnPaths:
    turn_number: int
    turn_dir: Path

    # Build one file path inside this turn directory.
    def file(self, name: str) -> Path:
        return self.turn_dir / name


# Store one human-readable transcript entry.
@dataclass(frozen=True)
class TranscriptEntry:
    turn_number: int
    operator_text: str | None
    assistant_text: str | None
    state: str | None
    operator_audio_path: Path | None = None
    assistant_audio_path: Path | None = None


# Persist per-turn phonecall artifacts under data/L22_phonecall.
class CallRunLogger:
    # Store root paths and create a stable call directory.
    def __init__(self, app_paths: AppPaths, *, call_id: str | None = None) -> None:
        self.app_paths = app_paths
        self.call_id = call_id or build_call_id()
        self.paths = CallRunPaths(
            call_id=self.call_id,
            call_dir=app_paths.calls_dir / self.call_id,
            report_path=app_paths.calls_dir / self.call_id / "call_report.json",
            transcript_path=app_paths.calls_dir / self.call_id / "call_transcript.md",
        )
        self.paths.call_dir.mkdir(parents=True, exist_ok=True)

    # Return or create paths for a numbered turn.
    def turn_paths(self, turn_number: int) -> TurnPaths:
        if turn_number < 1:
            raise ValueError("turn_number must be >= 1.")
        turn_dir = self.paths.call_dir / f"turn_{turn_number:03d}"
        turn_dir.mkdir(parents=True, exist_ok=True)
        return TurnPaths(turn_number=turn_number, turn_dir=turn_dir)

    # Save the raw operator response for one turn.
    def save_operator_raw(self, turn_number: int, payload: dict[str, Any]) -> Path:
        path = self.turn_paths(turn_number).file("operator.raw.json")
        write_json(path, mask_secret_fields(payload))
        return path

    # Save operator audio bytes exactly as received or decoded.
    def save_operator_audio(
        self,
        turn_number: int,
        audio_bytes: bytes,
        *,
        extension: str = "mp3",
    ) -> Path:
        path = self.turn_paths(turn_number).file(f"operator.audio.{clean_extension(extension)}")
        write_bytes(path, audio_bytes)
        return path

    # Save the text transcript used by downstream interpretation.
    def save_operator_transcript(self, turn_number: int, transcript: str) -> Path:
        path = self.turn_paths(turn_number).file("operator.transcript.txt")
        write_text(path, transcript)
        return path

    # Save the validated operator interpretation.
    def save_operator_interpretation(
        self,
        turn_number: int,
        interpretation: OperatorInterpretation | dict[str, Any],
    ) -> Path:
        path = self.turn_paths(turn_number).file("operator.interpretation.json")
        write_json(path, to_json_safe(interpretation))
        return path

    # Save the assistant plan before audio generation.
    def save_assistant_plan(
        self,
        turn_number: int,
        plan: AssistantPlan | dict[str, Any],
    ) -> Path:
        path = self.turn_paths(turn_number).file("assistant.plan.json")
        write_json(path, to_json_safe(plan))
        return path

    # Save the approved assistant utterance before TTS.
    def save_assistant_utterance(self, turn_number: int, utterance: str) -> Path:
        path = self.turn_paths(turn_number).file("assistant.utterance.txt")
        write_text(path, utterance)
        return path

    # Save the assistant audio generated from the approved utterance.
    def save_assistant_audio(self, turn_number: int, audio_bytes: bytes) -> Path:
        path = self.turn_paths(turn_number).file("assistant.audio.mp3")
        write_bytes(path, audio_bytes)
        return path

    # Save a masked Hub request for one turn.
    def save_hub_request(self, turn_number: int, request_payload: dict[str, Any]) -> Path:
        path = self.turn_paths(turn_number).file("hub_request.masked.json")
        write_json(path, mask_secret_fields(request_payload))
        return path

    # Save the raw Hub response for one turn.
    def save_hub_response(
        self,
        turn_number: int,
        response_payload: LoggedExchange | dict[str, Any],
    ) -> Path:
        path = self.turn_paths(turn_number).file("hub_response.raw.json")
        write_json(path, mask_secret_fields(to_json_safe(response_payload)))
        return path

    # Save the final machine-readable call report.
    def save_call_report(self, report: CallReport | dict[str, Any]) -> Path:
        write_json(self.paths.report_path, to_json_safe(report))
        return self.paths.report_path

    # Save one compact Markdown transcript with relative audio links.
    def save_call_transcript(self, entries: list[TranscriptEntry], *, mode: str | None = None) -> Path:
        lines = [f"# L22 Phonecall Transcript", "", f"Call ID: `{self.call_id}`", ""]
        if mode:
            lines.extend([f"Mode: `{mode}`", ""])
        for entry in entries:
            lines.extend(format_transcript_entry(entry, self.paths.call_dir))
        write_text(self.paths.transcript_path, "\n".join(lines).rstrip() + "\n")
        return self.paths.transcript_path

    # Rebuild the compact transcript from already persisted per-turn artifacts.
    def rebuild_call_transcript_from_artifacts(self, *, mode: str | None = None) -> Path:
        return self.save_call_transcript(self.collect_transcript_entries(), mode=mode)

    # Collect transcript entries from turn directories without trusting in-memory state.
    def collect_transcript_entries(self) -> list[TranscriptEntry]:
        entries: list[TranscriptEntry] = []
        if not self.paths.call_dir.exists():
            return entries
        for turn_dir in sorted(self.paths.call_dir.glob("turn_*")):
            if not turn_dir.is_dir():
                continue
            turn_number = parse_turn_number(turn_dir.name)
            if turn_number is None:
                continue
            entries.append(
                TranscriptEntry(
                    turn_number=turn_number,
                    operator_text=read_optional_text(turn_dir / "operator.transcript.txt"),
                    assistant_text=read_optional_text(turn_dir / "assistant.utterance.txt"),
                    state=read_optional_state(turn_dir / "operator.interpretation.json"),
                    operator_audio_path=find_first_existing(
                        turn_dir,
                        ("operator.audio.mp3", "operator.audio.wav", "operator.audio.m4a", "operator.audio.ogg"),
                    ),
                    assistant_audio_path=find_first_existing(turn_dir, ("assistant.audio.mp3",)),
                )
            )
        return entries


# Build a UTC timestamp call ID suitable for directory names.
def build_call_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


# Normalize a user-supplied extension to a safe file suffix.
def clean_extension(extension: str) -> str:
    cleaned = extension.strip().lower().lstrip(".")
    if not cleaned or any(character in cleaned for character in "\\/:*?\"<>|"):
        raise ValueError("Invalid audio extension.")
    return cleaned


# Convert dataclass-like app objects into JSON-safe values.
def to_json_safe(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return {key: to_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [to_json_safe(item) for item in value]
    return value


# Mask known secret field names recursively before writing JSON.
def mask_secret_fields(value: Any) -> Any:
    if isinstance(value, dict):
        masked: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in SECRET_FIELD_NAMES:
                masked[key] = REDACTED
            elif key.lower() in AUDIO_FIELD_NAMES and isinstance(item, str):
                masked[key] = summarize_transport_audio(item)
            elif key.lower() == "text" and isinstance(item, str) and looks_like_large_transport_text(item):
                masked[key] = summarize_transport_text(item)
            else:
                masked[key] = mask_secret_fields(item)
        return masked
    if isinstance(value, list):
        return [mask_secret_fields(item) for item in value]
    return value


# Summarize base64 audio transport strings instead of storing bulky blobs.
def summarize_transport_audio(value: str) -> dict[str, Any]:
    return {
        "transport": "base64_audio",
        "chars": len(value),
    }


# Return whether a raw response text likely duplicates bulky audio transport data.
def looks_like_large_transport_text(value: str) -> bool:
    return len(value) > 1000 and '"audio"' in value


# Summarize raw response text that contains bulky transport data.
def summarize_transport_text(value: str) -> dict[str, Any]:
    return {
        "transport": "large_response_text_omitted",
        "chars": len(value),
    }


# Write one JSON file using UTF-8 and stable formatting.
def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# Write one text file using UTF-8.
def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# Write one binary artifact.
def write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


# Parse a directory name such as turn_007 into its numeric turn.
def parse_turn_number(name: str) -> int | None:
    prefix = "turn_"
    if not name.startswith(prefix):
        return None
    suffix = name[len(prefix) :]
    if not suffix.isdigit():
        return None
    return int(suffix)


# Read a text artifact if it exists and has reviewable content.
def read_optional_text(path: Path) -> str | None:
    if not path.exists():
        return None
    content = path.read_text(encoding="utf-8").strip()
    return content or None


# Read the operator intent as the closest available per-turn state marker.
def read_optional_state(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    intent = payload.get("intent")
    if isinstance(intent, str) and intent:
        return f"operator_intent:{intent}"
    return None


# Return the first matching artifact from a small known filename set.
def find_first_existing(turn_dir: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        path = turn_dir / name
        if path.exists():
            return path
    matches = sorted(turn_dir.glob("operator.audio.*")) if any(name.startswith("operator.") for name in names) else []
    return matches[0] if matches else None


# Format one transcript entry as Markdown.
def format_transcript_entry(entry: TranscriptEntry, call_dir: Path) -> list[str]:
    lines = [f"## Turn {entry.turn_number:03d}", ""]
    lines.extend(["Operator:", f"> {entry.operator_text or ''}", ""])
    lines.extend(["Assistant:", f"> {entry.assistant_text or ''}", ""])
    if entry.state:
        lines.extend(["State:", f"`{entry.state}`", ""])
    audio_lines: list[str] = []
    if entry.operator_audio_path is not None:
        audio_lines.append(f"- operator: `{relative_artifact_path(entry.operator_audio_path, call_dir)}`")
    if entry.assistant_audio_path is not None:
        audio_lines.append(f"- assistant: `{relative_artifact_path(entry.assistant_audio_path, call_dir)}`")
    if audio_lines:
        lines.extend(["Audio:", *audio_lines, ""])
    return lines


# Return a call-directory-relative path for Markdown reports.
def relative_artifact_path(path: Path, call_dir: Path) -> str:
    try:
        return str(path.relative_to(call_dir)).replace("\\", "/")
    except ValueError:
        return path.name
