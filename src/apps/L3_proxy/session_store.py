# This module declares session persistence helpers for per-session conversation memory in the L3_proxy app.

from __future__ import annotations

import json
import re
from pathlib import Path

from .config import AppConfig
from .models import SessionData


SESSION_ID_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


# This helper normalizes a session ID so it is safe to use in a filename.
def normalize_session_id_for_path(session_id: str) -> str:
    cleaned = session_id.strip()
    if not cleaned:
        raise ValueError("session_id cannot be empty.")

    return SESSION_ID_FILENAME_PATTERN.sub("_", cleaned)


# This helper builds the JSON file path for one session.
def build_session_path(config: AppConfig, session_id: str) -> Path:
    normalized_session_id = normalize_session_id_for_path(session_id)
    return config.sessions_dir / f"{normalized_session_id}.json"


# This helper creates a new empty session object for a valid session ID.
def create_empty_session(session_id: str) -> SessionData:
    cleaned = session_id.strip()
    if not cleaned:
        raise ValueError("session_id cannot be empty.")

    return SessionData(session_id=cleaned)


# This function will load one session from JSON storage or create a new one.
def load_session(config: AppConfig, session_id: str) -> SessionData:
    session_path = build_session_path(config, session_id)
    if not session_path.exists():
        return create_empty_session(session_id)

    with session_path.open("r", encoding="utf-8") as session_file:
        payload = json.load(session_file)

    if not isinstance(payload, dict):
        raise ValueError(f"Session file must contain a JSON object: {session_path}")

    session_data = SessionData.from_dict(payload)
    if not session_data.session_id:
        raise ValueError(f"Session file is missing session_id: {session_path}")

    return session_data


# This function will persist one session into JSON storage.
def save_session(config: AppConfig, session_data: SessionData) -> Path:
    session_path = build_session_path(config, session_data.session_id)
    session_path.parent.mkdir(parents=True, exist_ok=True)

    with session_path.open("w", encoding="utf-8") as session_file:
        json.dump(
            session_data.to_dict(),
            session_file,
            ensure_ascii=False,
            indent=2,
        )
        session_file.write("\n")

    return session_path
