from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

from ..config import AppConfig, get_config
from ..data_loader import load_suspects
from ..models import Suspect
from ..output import ensure_output_directory, save_run_artifact


WORKBENCH_OUTPUT_DIR = Path("data") / "L2_findhim" / "output" / "workbench"


def get_config_with_session(timeout: int = 30) -> tuple[AppConfig, requests.Session, int]:
    config = get_config()
    session = requests.Session()
    return config, session, timeout


def get_first_suspect(config: AppConfig) -> Suspect:
    suspects = load_suspects(config.suspects_source_path)
    if not suspects:
        raise ValueError("No suspects found in the L1 verification result.")

    return suspects[0]


def get_all_suspects(config: AppConfig) -> list[Suspect]:
    suspects = load_suspects(config.suspects_source_path)
    if not suspects:
        raise ValueError("No suspects found in the L1 verification result.")

    return suspects


def save_workbench_artifact(filename: str, data: dict[str, Any]) -> Path:
    ensure_output_directory(WORKBENCH_OUTPUT_DIR)
    return save_run_artifact(WORKBENCH_OUTPUT_DIR / filename, data)


def load_workbench_artifact(filename: str) -> dict[str, Any]:
    artifact_path = WORKBENCH_OUTPUT_DIR / filename

    with artifact_path.open("r", encoding="utf-8") as file:
        return json.load(file)
