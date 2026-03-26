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
    openai_model: str
    max_agent_iterations: int
    data_dir: Path
    data_people_path: Path
    output_dir: Path
    output_json_path: Path
    access_level_api_url: str   


def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing.")
    
    return value


def get_config() -> AppConfig:
    data_dir = Path("data") / "EDU1"
    output_dir = data_dir / "output"
    data_people_path = data_dir / "input" / "data_people.json"

    return AppConfig(
        ai_devs_api_key=get_required_env("AI_DEVS_API_KEY"),
        openai_api_key=get_required_env("OPENAI_API_KEY"),
        openai_model="gpt-4o-mini",
        max_agent_iterations=8,
        data_dir=data_dir,
        data_people_path=data_people_path,
        output_dir=output_dir,
        output_json_path=output_dir / "app_status.json",
        access_level_api_url=get_required_env("L02_ACCESS_LEVEL_API_URL"),
    )