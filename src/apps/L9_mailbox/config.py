# Configuration loading for the L9 mailbox workbench.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

TASK_NAME = "mailbox"
MODEL_NAME = "gpt-5-mini"
REASONING_EFFORT = "low"
MAX_ITERATIONS = 20
MAX_SUBMIT_REQUESTS = 3
REQUEST_TIMEOUT_SECONDS = 30
MAX_TOOL_CALLS_PER_ITERATION = 1
DEFAULT_SEARCH_PAGE_SIZE = 5
MAX_MESSAGE_CHARS_PER_TOOL_RESULT = 4_000


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
    fetched_messages_file: Path


# Store secret-bearing external API configuration away from reportable data.
@dataclass(frozen=True)
class ExternalApiConfig:
    api_key: str
    zmail_url: str
    verify_url: str
    task_name: str = TASK_NAME


# Store LLM access and model settings for the bounded investigator loop.
@dataclass(frozen=True)
class LlmConfig:
    api_key: str
    model_name: str
    reasoning_effort: str


# Store hard limits that keep workbench runs bounded.
@dataclass(frozen=True)
class RuntimeConfig:
    max_iterations: int
    max_submit_requests: int
    request_timeout_seconds: int
    max_tool_calls_per_iteration: int
    default_search_page_size: int
    max_message_chars_per_tool_result: int


# Keep all loaded configuration in one object passed through future modules.
@dataclass(frozen=True)
class AppConfig:
    paths: AppPaths
    runtime: RuntimeConfig
    llm: LlmConfig | None
    external_api: ExternalApiConfig | None


# Build stable repository-relative paths for the mailbox workbench.
def build_app_paths() -> AppPaths:
    app_dir = Path(__file__).resolve().parent
    repo_root = Path(__file__).resolve().parents[3]
    docs_dir = app_dir / "docs"
    data_dir = repo_root / "data" / "L9_mailbox"
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
        fetched_messages_file=output_dir / "fetched_messages.json",
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


# Load external API config only when a run is allowed to use external services.
def load_external_api_config(*, required: bool) -> ExternalApiConfig | None:
    if (
        not required
        and not get_optional_env("AI_DEVS_API_KEY")
        and not get_optional_env("ZMAIL_API_URL")
        and not get_optional_env("HUB_VERIFY_URL")
    ):
        return None

    return ExternalApiConfig(
        api_key=get_required_env("AI_DEVS_API_KEY"),
        zmail_url=get_required_env("ZMAIL_API_URL"),
        verify_url=get_required_env("HUB_VERIFY_URL"),
    )


# Load LLM config only when a run is allowed to call OpenAI.
def load_llm_config(*, required: bool) -> LlmConfig | None:
    if not required and not get_optional_env("OPENAI_API_KEY"):
        return None

    return LlmConfig(
        api_key=get_required_env("OPENAI_API_KEY"),
        model_name=MODEL_NAME,
        reasoning_effort=REASONING_EFFORT,
    )


# Load app-level guard settings that keep searches, submissions, and API calls bounded.
def load_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        max_iterations=MAX_ITERATIONS,
        max_submit_requests=MAX_SUBMIT_REQUESTS,
        request_timeout_seconds=REQUEST_TIMEOUT_SECONDS,
        max_tool_calls_per_iteration=MAX_TOOL_CALLS_PER_ITERATION,
        default_search_page_size=DEFAULT_SEARCH_PAGE_SIZE,
        max_message_chars_per_tool_result=MAX_MESSAGE_CHARS_PER_TOOL_RESULT,
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


# Create local runtime directories before future workflow steps write files.
def ensure_runtime_directories(paths: AppPaths) -> None:
    for path in (
        paths.data_dir,
        paths.logs_dir,
        paths.output_dir,
        paths.cache_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)


# Return a secret-safe summary for setup checks and future diagnostics.
def build_safe_config_summary(config: AppConfig) -> dict[str, object]:
    return {
        "app": "L9_mailbox",
        "data_dir": str(config.paths.data_dir.relative_to(config.paths.repo_root)),
        "llm": {
            "loaded": config.llm is not None,
            "api_key": "configured" if config.llm else "not_loaded",
            "model_name": config.llm.model_name if config.llm else None,
            "reasoning_effort": config.llm.reasoning_effort if config.llm else None,
        },
        "runtime": {
            "max_iterations": config.runtime.max_iterations,
            "max_submit_requests": config.runtime.max_submit_requests,
            "request_timeout_seconds": config.runtime.request_timeout_seconds,
            "max_tool_calls_per_iteration": config.runtime.max_tool_calls_per_iteration,
            "default_search_page_size": config.runtime.default_search_page_size,
            "max_message_chars_per_tool_result": config.runtime.max_message_chars_per_tool_result,
        },
        "external_api": {
            "loaded": config.external_api is not None,
            "api_key": "configured" if config.external_api else "not_loaded",
            "zmail_url": "configured" if config.external_api else "not_loaded",
            "verify_url": "configured" if config.external_api else "not_loaded",
        },
    }
