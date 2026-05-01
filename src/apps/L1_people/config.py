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
    people_csv_url: str
    verify_api_url: str
    openai_model: str
    data_dir: Path
    input_dir: Path
    input_csv_path: Path
    output_dir: Path
    output_json_path: Path


def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing.")

    return value


def get_config() -> AppConfig:
    data_dir = Path("data") / "L1_people"
    input_dir = data_dir / "input"
    input_csv_path = input_dir / "people.csv"
    output_dir = data_dir / "output"
    output_json_path = output_dir / "verification_result.json"

    return AppConfig(
        ai_devs_api_key=get_required_env("AI_DEVS_API_KEY"),
        openai_api_key=get_required_env("OPENAI_API_KEY"),
        task_name="people",
        people_csv_url=get_required_env("L1_PEOPLE_CSV_URL"),
        verify_api_url=get_required_env("L1_VERIFY_API_URL"),
        openai_model="gpt-4.1-mini",
        data_dir=data_dir,
        input_dir=input_dir,
        input_csv_path=input_csv_path,
        output_dir=output_dir,
        output_json_path=output_json_path
    )
