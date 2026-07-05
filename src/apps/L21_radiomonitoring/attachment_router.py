# Decode and route Base64 attachments before any model call.

from __future__ import annotations

import base64
import csv
import hashlib
import json
from io import StringIO
from pathlib import Path
from typing import Any

from PIL import Image

from src.apps.L21_radiomonitoring.config import AppConfig
from src.apps.L21_radiomonitoring.models import AttachmentArtifact, CapturedSignal


TEXT_MIME_TYPES = {"text/plain", "text/csv", "application/csv"}
JSON_MIME_TYPES = {"application/json", "text/json"}
IMAGE_MIME_PREFIX = "image/"
AUDIO_MIME_PREFIX = "audio/"


# Guess a stable file extension from the attachment MIME type.
def extension_for_mime(mime_type: str) -> str:
    normalized = mime_type.lower().split(";")[0].strip()
    if normalized == "image/png":
        return ".png"
    if normalized in {"image/jpeg", "image/jpg"}:
        return ".jpg"
    if normalized in {"audio/mpeg", "audio/mp3", "audio/mpga"}:
        return ".mp3"
    if normalized in JSON_MIME_TYPES:
        return ".json"
    if normalized in {"text/csv", "application/csv"}:
        return ".csv"
    if normalized.startswith("text/"):
        return ".txt"
    return ".bin"


# Select the local processing route for one MIME type.
def route_for_mime(mime_type: str) -> str:
    normalized = mime_type.lower().split(";")[0].strip()
    if normalized.startswith(IMAGE_MIME_PREFIX):
        return "image"
    if normalized.startswith(AUDIO_MIME_PREFIX):
        return "audio"
    if normalized in JSON_MIME_TYPES:
        return "json"
    if normalized in {"text/csv", "application/csv"}:
        return "csv"
    if normalized in TEXT_MIME_TYPES or normalized.startswith("text/"):
        return "text"
    return "unknown"


# Decode one attachment signal to disk and return its local artifact metadata.
def decode_attachment(config: AppConfig, signal: CapturedSignal) -> AttachmentArtifact:
    payload = signal.payload
    raw_base64 = str(payload.get("attachment", ""))
    if not raw_base64:
        raise ValueError(f"Signal {signal.sequence} has no attachment payload.")

    decoded_bytes = base64.b64decode(raw_base64)
    sha256 = hashlib.sha256(decoded_bytes).hexdigest()
    mime_type = str(payload.get("meta", "application/octet-stream")).strip()
    route = route_for_mime(mime_type)
    output_path = config.paths.attachments_dir / f"{signal.sequence:03d}_{sha256[:16]}{extension_for_mime(mime_type)}"
    output_path.write_bytes(decoded_bytes)

    width: int | None = None
    height: int | None = None
    if route == "image":
        with Image.open(output_path) as image:
            width, height = image.size
        if width * height > config.runtime.max_image_pixels:
            raise ValueError(
                f"Image attachment {output_path.name} exceeds max pixel guard."
            )

    return AttachmentArtifact(
        signal_sequence=signal.sequence,
        mime_type=mime_type,
        source_filesize=payload.get("filesize") if isinstance(payload.get("filesize"), int) else None,
        decoded_size=len(decoded_bytes),
        sha256=sha256,
        path=str(output_path.relative_to(config.paths.repo_root)),
        route=route,  # type: ignore[arg-type]
        width=width,
        height=height,
    )


# Try to parse a decoded structured attachment without using a model.
def parse_decoded_attachment(config: AppConfig, artifact: AttachmentArtifact) -> Any | None:
    path = config.paths.repo_root / artifact.path
    if artifact.route == "json":
        return json.loads(path.read_text(encoding="utf-8"))
    if artifact.route == "text":
        return path.read_text(encoding="utf-8", errors="replace")
    if artifact.route == "csv":
        text = path.read_text(encoding="utf-8", errors="replace")
        return list(csv.DictReader(StringIO(text)))
    return None
