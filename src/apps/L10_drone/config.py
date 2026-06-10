# Configuration loading for the L10 drone workflow.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

TASK_NAME = "drone"
POWER_PLANT_CODE = "PWR6132PL"
DAM_COLUMN = 2
DAM_ROW = 4
PLANNER_MODEL = "gpt-5-mini"
REASONING_EFFORT = "low"
MAX_VERIFY_ATTEMPTS = 5
REQUEST_TIMEOUT_SECONDS = 30
MAX_INSTRUCTIONS = 20
MAX_INSTRUCTION_CHARS = 500
MAX_CHANGE_SUMMARY_CHARS = 800


# Keep repository and runtime paths in one explicit object.
@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    app_dir: Path
    docs_dir: Path
    data_dir: Path
    input_dir: Path
    logs_dir: Path
    cache_dir: Path
    drone_map_file: Path
    drone_docs_file: Path


# Store mission facts that should stay outside model guesswork.
@dataclass(frozen=True)
class MissionConfig:
    task_name: str
    power_plant_code: str
    dam_column: int
    dam_row: int


# Store secret-bearing Hub configuration away from reportable data.
@dataclass(frozen=True)
class HubConfig:
    api_key: str
    verify_url: str
    task_name: str = TASK_NAME


# Store OpenAI access and model settings for the planner step.
@dataclass(frozen=True)
class LlmConfig:
    api_key: str
    model_name: str
    reasoning_effort: str


# Store hard limits that keep the local repair loop bounded.
@dataclass(frozen=True)
class RuntimeConfig:
    max_verify_attempts: int
    request_timeout_seconds: int
    max_instructions: int
    max_instruction_chars: int
    max_change_summary_chars: int


# Keep all loaded configuration in one object passed through the app.
@dataclass(frozen=True)
class AppConfig:
    paths: AppPaths
    mission: MissionConfig
    runtime: RuntimeConfig
    llm: LlmConfig | None
    hub: HubConfig | None


# Build stable repository-relative paths for the drone app.
def build_app_paths() -> AppPaths:
    app_dir = Path(__file__).resolve().parent
    repo_root = Path(__file__).resolve().parents[3]
    docs_dir = app_dir / "docs"
    data_dir = repo_root / "data" / "L10_drone"
    input_dir = data_dir / "input"
    logs_dir = data_dir / "logs"
    cache_dir = data_dir / "cache"

    return AppPaths(
        repo_root=repo_root,
        app_dir=app_dir,
        docs_dir=docs_dir,
        data_dir=data_dir,
        input_dir=input_dir,
        logs_dir=logs_dir,
        cache_dir=cache_dir,
        drone_map_file=input_dir / "drone.png",
        drone_docs_file=input_dir / "drone.html",
    )


# Read one required environment variable and fail with a clear setup error.
def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing.")
    return value


# Read one optional environment variable and normalize empty strings to None.
def get_optional_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


# Load mission facts that the model should not infer.
def load_mission_config() -> MissionConfig:
    return MissionConfig(
        task_name=TASK_NAME,
        power_plant_code=POWER_PLANT_CODE,
        dam_column=DAM_COLUMN,
        dam_row=DAM_ROW,
    )


# Load Hub config only when a run is allowed to use the external verifier.
def load_hub_config(*, required: bool) -> HubConfig | None:
    if (
        not required
        and not get_optional_env("AI_DEVS_API_KEY")
        and not get_optional_env("HUB_VERIFY_URL")
    ):
        return None

    return HubConfig(
        api_key=get_required_env("AI_DEVS_API_KEY"),
        verify_url=get_required_env("HUB_VERIFY_URL"),
    )


# Load LLM config only when a run is allowed to call OpenAI.
def load_llm_config(*, required: bool) -> LlmConfig | None:
    if not required and not get_optional_env("OPENAI_API_KEY"):
        return None

    return LlmConfig(
        api_key=get_required_env("OPENAI_API_KEY"),
        model_name=PLANNER_MODEL,
        reasoning_effort=REASONING_EFFORT,
    )


# Load app-level guard settings.
def load_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        max_verify_attempts=MAX_VERIFY_ATTEMPTS,
        request_timeout_seconds=REQUEST_TIMEOUT_SECONDS,
        max_instructions=MAX_INSTRUCTIONS,
        max_instruction_chars=MAX_INSTRUCTION_CHARS,
        max_change_summary_chars=MAX_CHANGE_SUMMARY_CHARS,
    )


# Load all app config while allowing tests to skip secret-bearing config.
def load_app_config(
    *,
    require_hub: bool = True,
    require_llm: bool = True,
) -> AppConfig:
    return AppConfig(
        paths=build_app_paths(),
        mission=load_mission_config(),
        runtime=load_runtime_config(),
        llm=load_llm_config(required=require_llm),
        hub=load_hub_config(required=require_hub),
    )


# Create local runtime directories before workflow steps write files.
def ensure_runtime_directories(paths: AppPaths) -> None:
    for path in (paths.data_dir, paths.input_dir, paths.logs_dir, paths.cache_dir):
        path.mkdir(parents=True, exist_ok=True)


# Return a secret-safe summary for logs and setup diagnostics.
def build_safe_config_summary(config: AppConfig) -> dict[str, object]:
    return {
        "app": "L10_drone",
        "data_dir": str(config.paths.data_dir.relative_to(config.paths.repo_root)),
        "input_dir": str(config.paths.input_dir.relative_to(config.paths.repo_root)),
        "mission": {
            "task_name": config.mission.task_name,
            "power_plant_code": config.mission.power_plant_code,
            "dam_column": config.mission.dam_column,
            "dam_row": config.mission.dam_row,
        },
        "llm": {
            "loaded": config.llm is not None,
            "api_key": "configured" if config.llm else "not_loaded",
            "model_name": config.llm.model_name if config.llm else None,
            "reasoning_effort": config.llm.reasoning_effort if config.llm else None,
        },
        "runtime": {
            "max_verify_attempts": config.runtime.max_verify_attempts,
            "request_timeout_seconds": config.runtime.request_timeout_seconds,
            "max_instructions": config.runtime.max_instructions,
            "max_instruction_chars": config.runtime.max_instruction_chars,
            "max_change_summary_chars": config.runtime.max_change_summary_chars,
        },
        "hub": {
            "loaded": config.hub is not None,
            "api_key": "configured" if config.hub else "not_loaded",
            "verify_url": "configured" if config.hub else "not_loaded",
        },
    }
