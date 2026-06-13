# Configuration loading for the bounded L12 firmware agent.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

TASK_NAME = "firmware"
MODEL_NAME = "gpt-5.5"
REASONING_EFFORT = "medium"
MAX_MODEL_CALLS = 30
MAX_SHELL_REQUESTS = 20
MAX_SUBMIT_REQUESTS = 1
MAX_OUTPUT_TOKENS = 2_000
MAX_TOTAL_REPORTED_TOKENS = 150_000
MAX_COMMAND_CHARS = 300
MAX_SHELL_RESULT_CHARS = 6_000
REQUEST_TIMEOUT_SECONDS = 30


# Keep repository and runtime paths in one explicit object.
@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    app_dir: Path
    docs_dir: Path
    data_dir: Path
    logs_dir: Path
    output_dir: Path
    cache_dir: Path
    run_report_file: Path


# Store OpenAI access and model settings for the agent loop.
@dataclass(frozen=True)
class LlmConfig:
    api_key: str
    model_name: str
    reasoning_effort: str


# Store secret-bearing course API configuration away from reportable data.
@dataclass(frozen=True)
class ExternalApiConfig:
    api_key: str
    shell_url: str
    verify_url: str
    task_name: str = TASK_NAME


# Store hard limits that bound cost, context, and external requests.
@dataclass(frozen=True)
class RuntimeConfig:
    max_model_calls: int
    max_shell_requests: int
    max_submit_requests: int
    max_output_tokens: int
    max_total_reported_tokens: int
    max_command_chars: int
    max_shell_result_chars: int
    request_timeout_seconds: int


# Keep all loaded configuration in one object passed through the app.
@dataclass(frozen=True)
class AppConfig:
    paths: AppPaths
    runtime: RuntimeConfig
    llm: LlmConfig | None
    external_api: ExternalApiConfig | None


# Build stable repository-relative paths for the firmware workbench.
def build_app_paths() -> AppPaths:
    app_dir = Path(__file__).resolve().parent
    repo_root = Path(__file__).resolve().parents[3]
    docs_dir = app_dir / "docs"
    data_dir = repo_root / "data" / "L12_firmware"
    logs_dir = data_dir / "logs"
    output_dir = data_dir / "output"
    cache_dir = data_dir / "cache"

    return AppPaths(
        repo_root=repo_root,
        app_dir=app_dir,
        docs_dir=docs_dir,
        data_dir=data_dir,
        logs_dir=logs_dir,
        output_dir=output_dir,
        cache_dir=cache_dir,
        run_report_file=output_dir / "run_report.json",
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


# Load OpenAI config only when a run is allowed to call the model.
def load_llm_config(*, required: bool) -> LlmConfig | None:
    if not required and not get_optional_env("OPENAI_API_KEY"):
        return None

    return LlmConfig(
        api_key=get_required_env("OPENAI_API_KEY"),
        model_name=MODEL_NAME,
        reasoning_effort=REASONING_EFFORT,
    )


# Load course API config only when a run is allowed to use external services.
def load_external_api_config(*, required: bool) -> ExternalApiConfig | None:
    if not required and not get_optional_env("FIRMWARE_SHELL_URL"):
        return None

    return ExternalApiConfig(
        api_key=get_required_env("AI_DEVS_API_KEY"),
        shell_url=get_required_env("FIRMWARE_SHELL_URL"),
        verify_url=get_required_env("HUB_VERIFY_URL"),
    )


# Load app-level guard settings from fixed, reviewable constants.
def load_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        max_model_calls=MAX_MODEL_CALLS,
        max_shell_requests=MAX_SHELL_REQUESTS,
        max_submit_requests=MAX_SUBMIT_REQUESTS,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        max_total_reported_tokens=MAX_TOTAL_REPORTED_TOKENS,
        max_command_chars=MAX_COMMAND_CHARS,
        max_shell_result_chars=MAX_SHELL_RESULT_CHARS,
        request_timeout_seconds=REQUEST_TIMEOUT_SECONDS,
    )


# Load all app config while allowing local checks to skip secret-bearing config.
def load_app_config(
    *,
    require_external_api: bool = True,
    require_llm: bool = True,
) -> AppConfig:
    return AppConfig(
        paths=build_app_paths(),
        runtime=load_runtime_config(),
        llm=load_llm_config(required=require_llm),
        external_api=load_external_api_config(required=require_external_api),
    )


# Create ignored runtime directories before future workflow steps write files.
def ensure_runtime_directories(paths: AppPaths) -> None:
    for path in (
        paths.data_dir,
        paths.logs_dir,
        paths.output_dir,
        paths.cache_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)


# Return a secret-safe summary for setup checks and future reports.
def build_safe_config_summary(config: AppConfig) -> dict[str, object]:
    return {
        "app": "L12_firmware",
        "data_dir": str(config.paths.data_dir.relative_to(config.paths.repo_root)),
        "output_dir": str(config.paths.output_dir.relative_to(config.paths.repo_root)),
        "llm": {
            "loaded": config.llm is not None,
            "api_key": "configured" if config.llm else "not_loaded",
            "model_name": config.llm.model_name if config.llm else None,
            "reasoning_effort": config.llm.reasoning_effort if config.llm else None,
        },
        "runtime": {
            "max_model_calls": config.runtime.max_model_calls,
            "max_shell_requests": config.runtime.max_shell_requests,
            "max_submit_requests": config.runtime.max_submit_requests,
            "max_output_tokens": config.runtime.max_output_tokens,
            "max_total_reported_tokens": config.runtime.max_total_reported_tokens,
            "max_command_chars": config.runtime.max_command_chars,
            "max_shell_result_chars": config.runtime.max_shell_result_chars,
            "request_timeout_seconds": config.runtime.request_timeout_seconds,
        },
        "external_api": {
            "loaded": config.external_api is not None,
            "api_key": "configured" if config.external_api else "not_loaded",
            "shell_url": "configured" if config.external_api else "not_loaded",
            "verify_url": "configured" if config.external_api else "not_loaded",
            "task_name": (
                config.external_api.task_name
                if config.external_api
                else TASK_NAME
            ),
        },
    }
