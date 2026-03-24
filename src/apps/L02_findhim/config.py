"""This file loads app settings such as API keys, URLs, paths, and model configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    ai_devs_api_key: str
    openai_api_key: str
    task_name: str
    openai_model: str
    max_agent_iterations: int
    data_dir: Path
    output_dir: Path
    output_json_path: Path
    suspects_source_path: Path
    power_plants_url: str
    location_api_url: str
    access_level_api_url: str
    verify_api_url: str


def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing.")

    return value


def get_config() -> AppConfig:
    data_dir = Path("data") / "L02_findhim"
    output_dir = data_dir / "output"

    return AppConfig(
        ai_devs_api_key=get_required_env("AI_DEVS_API_KEY"),
        openai_api_key=get_required_env("OPENAI_API_KEY"),
        task_name="findhim",
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini").strip(),
        max_agent_iterations=int(os.getenv("L02_MAX_AGENT_ITERATIONS", "12")),
        data_dir=data_dir,
        output_dir=output_dir,
        output_json_path=output_dir / "app_status.json",
        suspects_source_path=Path("data") / "L01_people" / "output" / "verification_result.json",
        power_plants_url=get_required_env("L02_POWER_PLANTS_URL"),
        location_api_url=get_required_env("L02_LOCATION_API_URL"),
        access_level_api_url=get_required_env("L02_ACCESS_LEVEL_API_URL"),
        verify_api_url=get_required_env("L02_VERIFY_API_URL"),
    )
