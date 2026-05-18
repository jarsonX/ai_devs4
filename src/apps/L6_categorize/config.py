# Path and environment configuration for the L6 categorize learning app.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

TASK_NAME = "categorize"


# Store repository-relative paths used by the categorize workflow.
@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    app_dir: Path
    docs_dir: Path
    data_dir: Path
    input_dir: Path
    output_dir: Path
    latest_csv_file: Path
    run_report_file: Path


# Store Hub configuration required for categorize requests.
@dataclass(frozen=True)
class HubConfig:
    api_key: str
    data_url: str
    verify_url: str
    task_name: str = TASK_NAME


# Store all configuration needed by the CLI workflow.
@dataclass(frozen=True)
class AppConfig:
    paths: AppPaths
    hub: HubConfig


# Build stable repository-relative paths for categorize inputs and outputs.
def build_app_paths() -> AppPaths:
    repo_root = Path(__file__).resolve().parents[3]
    app_dir = Path(__file__).resolve().parent
    docs_dir = app_dir / "docs"
    data_dir = repo_root / "data" / "L6_categorize"
    input_dir = data_dir / "input"
    output_dir = data_dir / "output"

    return AppPaths(
        repo_root=repo_root,
        app_dir=app_dir,
        docs_dir=docs_dir,
        data_dir=data_dir,
        input_dir=input_dir,
        output_dir=output_dir,
        latest_csv_file=input_dir / "categorize_latest.csv",
        run_report_file=output_dir / "run_report.json",
    )


# Read one required environment variable and fail with a clear setup error.
def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing.")

    return value


# Load the Hub configuration required by the categorize workflow.
def load_hub_config() -> HubConfig:
    return HubConfig(
        api_key=get_required_env("AI_DEVS_API_KEY"),
        data_url=get_required_env("HUB_DATA_URL"),
        verify_url=get_required_env("HUB_VERIFY_URL"),
    )


# Load all application configuration from paths and environment variables.
def load_app_config() -> AppConfig:
    return AppConfig(
        paths=build_app_paths(),
        hub=load_hub_config(),
    )


# Create local runtime directories needed by later workflow steps.
def ensure_runtime_directories(paths: AppPaths) -> None:
    for path in (
        paths.data_dir,
        paths.input_dir,
        paths.output_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
