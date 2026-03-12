from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import requests

from .config import AppConfig
from .models import PersonRecord


def build_people_csv_url(config: AppConfig) -> str:
    return f"{config.hub_base_url}/data/{config.api_key}/people.csv"


def ensure_input_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def download_people_csv(config: AppConfig, timeout: int = 30) -> Path:
    ensure_input_directory(config.input_dir)

    url = build_people_csv_url(config)
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()

    config.input_csv_path.write_bytes(response.content)
    return config.input_csv_path


def load_people_csv(csv_path: Path) -> list[dict[str, Any]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:          ## encoding
        reader = csv.DictReader(file)
        return list(reader)
    

def map_row_to_person(row: dict[str, Any]) -> PersonRecord:
    return PersonRecord(
        name=str(row["name"]).strip(),
        surname=str(row["surname"]).strip(),
        gender=str(row["gender"]).strip(),
        birth_date=str(row["birthDate"]).strip(),
        birth_place=str(row["birthPlace"]).strip(),
        job=str(row["job"]).strip(),
    )


def load_people(csv_path: Path) -> list[PersonRecord]:
    rows = load_people_csv(csv_path)
    return [map_row_to_person(row) for row in rows]