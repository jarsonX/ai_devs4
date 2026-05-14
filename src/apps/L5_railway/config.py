# Path and environment configuration for the L5 railway learning app.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


# Store repository-relative paths used by the railway workflow.
@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    app_dir: Path
    docs_dir: Path
    data_dir: Path
    output_dir: Path
    help_response_file: Path
    request_log_file: Path
    response_log_file: Path
    run_report_file: Path


# Store secret-bearing Hub configuration for explicit API calls.
@dataclass(frozen=True)
class HubConfig:
    api_key: str
    verify_url: str
    task_name: str


# Build stable repository-relative paths for railway inputs and outputs.
def build_app_paths() -> AppPaths:
    repo_root = Path(__file__).resolve().parents[3]
    app_dir = Path(__file__).resolve().parent
    docs_dir = app_dir / "docs"
    data_dir = repo_root / "data" / "L5_railway"
    output_dir = data_dir / "output"

    return AppPaths(
        repo_root=repo_root,
        app_dir=app_dir,
        docs_dir=docs_dir,
        data_dir=data_dir,
        output_dir=output_dir,
        help_response_file=output_dir / "help_response.json",
        request_log_file=output_dir / "request_log.jsonl",
        response_log_file=output_dir / "response_log.jsonl",
        run_report_file=output_dir / "run_report.md",
    )


# Load the Hub configuration required by the future railway workflow.
def load_hub_config() -> HubConfig:
    return HubConfig(
        api_key=get_required_env("AI_DEVS_API_KEY"),
        verify_url=get_required_env("HUB_VERIFY_URL"),
        task_name="railway",
    )


# Read one required environment variable and fail with a clear setup error.
def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing.")

    return value
