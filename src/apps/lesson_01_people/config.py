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
    hub_base_url: str
    openai_model: str
    data_dir: Path
    input_dir: Path
    input_csv_path: Path


def get_config() -> AppConfig:
    ai_devs_api_key = os.getenv("AI_DEVS_API_KEY", "").strip()
    if not ai_devs_api_key:
        raise ValueError("AI_DEVS_API_KEY is missing.")

    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY is missing.")    
    
    data_dir = Path("data") / "lesson_01_people"
    input_dir = data_dir / "input"
    input_csv_path = input_dir / "people.csv"

    return AppConfig(
        ai_devs_api_key=ai_devs_api_key,
        openai_api_key=openai_api_key,
        task_name="people",
        hub_base_url="https://hub.ag3nts.org",
        openai_model="gpt-4.1-mini",
        data_dir=data_dir,
        input_dir=input_dir,
        input_csv_path=input_csv_path
    )