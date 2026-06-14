# Configuration loading for the deterministic L13 reactor controller.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

TASK_NAME = "reactor"
BOARD_WIDTH = 7
BOARD_HEIGHT = 5
START_COLUMN = 1
GOAL_COLUMN = 7
ROBOT_ROW = 5
MAX_COMMANDS = 100
REQUEST_TIMEOUT_SECONDS = 30


# Keep repository and runtime paths in one explicit object.
@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    app_dir: Path
    data_dir: Path
    logs_dir: Path


# Store secret-bearing Hub configuration away from reportable data.
@dataclass(frozen=True)
class HubConfig:
    api_key: str
    verify_url: str
    task_name: str = TASK_NAME


# Store deterministic board facts and execution limits.
@dataclass(frozen=True)
class RuntimeConfig:
    board_width: int
    board_height: int
    start_column: int
    goal_column: int
    robot_row: int
    max_commands: int
    request_timeout_seconds: int


# Keep all reactor configuration in one object passed through the workflow.
@dataclass(frozen=True)
class AppConfig:
    paths: AppPaths
    hub: HubConfig
    runtime: RuntimeConfig


# Read one required environment variable and fail with a clear setup error.
def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing.")
    return value


# Build stable repository-relative paths for reactor runtime data.
def build_app_paths() -> AppPaths:
    app_dir = Path(__file__).resolve().parent
    repo_root = Path(__file__).resolve().parents[3]
    data_dir = repo_root / "data" / "L13_reactor"
    return AppPaths(
        repo_root=repo_root,
        app_dir=app_dir,
        data_dir=data_dir,
        logs_dir=data_dir / "logs",
    )


# Load all settings required for a real reactor run.
def load_app_config() -> AppConfig:
    return AppConfig(
        paths=build_app_paths(),
        hub=HubConfig(
            api_key=get_required_env("AI_DEVS_API_KEY"),
            verify_url=get_required_env("HUB_VERIFY_URL"),
        ),
        runtime=RuntimeConfig(
            board_width=BOARD_WIDTH,
            board_height=BOARD_HEIGHT,
            start_column=START_COLUMN,
            goal_column=GOAL_COLUMN,
            robot_row=ROBOT_ROW,
            max_commands=MAX_COMMANDS,
            request_timeout_seconds=REQUEST_TIMEOUT_SECONDS,
        ),
    )


# Create ignored runtime directories before writing command history.
def ensure_runtime_directories(paths: AppPaths) -> None:
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
