# Configuration loading for the L8 failure log-condensation app.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

TASK_NAME = "failure"
DEFAULT_CLASSIFIER_MODEL = "gpt-5-mini"
DEFAULT_REPAIR_MODEL = "gpt-5"
DEFAULT_BATCH_SIZE = 80
DEFAULT_MAX_MODEL_REQUESTS = 20
DEFAULT_MAX_VERIFY_REQUESTS = 5
DEFAULT_TOKEN_LIMIT = 1500
DEFAULT_TARGET_TOKEN_LIMIT = 1300


# Keep all repository and app data paths in one easy-to-audit object.
@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    app_dir: Path
    docs_dir: Path
    data_dir: Path
    input_dir: Path
    output_dir: Path
    logs_dir: Path
    cache_dir: Path
    source_log_file: Path
    profile_file: Path
    candidates_file: Path
    classified_events_file: Path
    condensed_logs_file: Path
    run_report_file: Path


# Store Hub secrets and endpoint config away from reportable workflow data.
@dataclass(frozen=True)
class HubConfig:
    api_key: str
    verify_url: str
    task_name: str = TASK_NAME


# Store OpenAI model settings used by the narrow classification step.
@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    classifier_model: str
    repair_model: str


# Hold the guardrails that stop runaway model or Hub loops.
@dataclass(frozen=True)
class RuntimeConfig:
    max_verify_requests: int
    max_model_requests: int
    token_limit: int
    target_token_limit: int
    batch_size: int


# Keep all loaded configuration in one object passed through the workflow.
@dataclass(frozen=True)
class AppConfig:
    paths: AppPaths
    runtime: RuntimeConfig
    hub: HubConfig | None
    openai: OpenAIConfig | None


# Build stable repository-relative paths for L8 inputs and outputs.
def build_app_paths() -> AppPaths:
    app_dir = Path(__file__).resolve().parent
    repo_root = Path(__file__).resolve().parents[3]
    docs_dir = app_dir / "docs"
    data_dir = repo_root / "data" / "L8_failure"
    input_dir = data_dir / "input"
    output_dir = data_dir / "output"
    logs_dir = data_dir / "logs"
    cache_dir = data_dir / "cache"

    return AppPaths(
        repo_root=repo_root,
        app_dir=app_dir,
        docs_dir=docs_dir,
        data_dir=data_dir,
        input_dir=input_dir,
        output_dir=output_dir,
        logs_dir=logs_dir,
        cache_dir=cache_dir,
        source_log_file=input_dir / "logs.txt",
        profile_file=output_dir / "profile.json",
        candidates_file=output_dir / "candidates.jsonl",
        classified_events_file=output_dir / "classified_events.jsonl",
        condensed_logs_file=output_dir / "condensed_logs.txt",
        run_report_file=output_dir / "run_report.json",
    )


# Read one required environment variable and explain the missing setup clearly.
def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing.")
    return value


# Read one optional environment variable and normalize empty strings to None.
def get_optional_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


# Parse one positive integer environment variable with a clear lower-bound error.
def get_optional_int_env(name: str, default: int, minimum: int = 1) -> int:
    value = get_optional_env(name)
    if value is None:
        return default

    try:
        parsed_value = int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer.") from error

    if parsed_value < minimum:
        raise ValueError(f"{name} must be >= {minimum}.")

    return parsed_value


# Load the Hub config only when a run is allowed to verify externally.
def load_hub_config(*, required: bool) -> HubConfig | None:
    if not required and not get_optional_env("AI_DEVS_API_KEY") and not get_optional_env("HUB_VERIFY_URL"):
        return None

    return HubConfig(
        api_key=get_required_env("AI_DEVS_API_KEY"),
        verify_url=get_required_env("HUB_VERIFY_URL"),
    )


# Load OpenAI config only when the workflow will call the local classifier model.
def load_openai_config(*, required: bool) -> OpenAIConfig | None:
    if not required and not get_optional_env("OPENAI_API_KEY"):
        return None

    return OpenAIConfig(
        api_key=get_required_env("OPENAI_API_KEY"),
        classifier_model=get_optional_env("L8_FAILURE_CLASSIFIER_MODEL") or DEFAULT_CLASSIFIER_MODEL,
        repair_model=get_optional_env("L8_FAILURE_REPAIR_MODEL") or DEFAULT_REPAIR_MODEL,
    )


# Load runtime limits that keep the exercise workflow bounded and repeatable.
def load_runtime_config() -> RuntimeConfig:
    token_limit = get_optional_int_env("L8_FAILURE_TOKEN_LIMIT", DEFAULT_TOKEN_LIMIT)
    target_token_limit = get_optional_int_env(
        "L8_FAILURE_TARGET_TOKEN_LIMIT",
        DEFAULT_TARGET_TOKEN_LIMIT,
    )
    if target_token_limit > token_limit:
        raise ValueError("L8_FAILURE_TARGET_TOKEN_LIMIT must be <= L8_FAILURE_TOKEN_LIMIT.")

    return RuntimeConfig(
        max_verify_requests=get_optional_int_env(
            "L8_FAILURE_MAX_VERIFY_REQUESTS",
            DEFAULT_MAX_VERIFY_REQUESTS,
        ),
        max_model_requests=get_optional_int_env(
            "L8_FAILURE_MAX_MODEL_REQUESTS",
            DEFAULT_MAX_MODEL_REQUESTS,
        ),
        token_limit=token_limit,
        target_token_limit=target_token_limit,
        batch_size=get_optional_int_env("L8_FAILURE_BATCH_SIZE", DEFAULT_BATCH_SIZE),
    )


# Load app config with optional secret-bearing sections for diagnostic runs.
def load_app_config(
    *,
    require_openai: bool = True,
    require_hub: bool = True,
) -> AppConfig:
    return AppConfig(
        paths=build_app_paths(),
        runtime=load_runtime_config(),
        hub=load_hub_config(required=require_hub),
        openai=load_openai_config(required=require_openai),
    )


# Create local runtime directories before files are written into them.
def ensure_runtime_directories(paths: AppPaths) -> None:
    for path in (
        paths.data_dir,
        paths.input_dir,
        paths.output_dir,
        paths.logs_dir,
        paths.cache_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
