# Configuration loading for the L11 evaluation sensor-anomaly app.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

TASK_NAME = "evaluation"
NOTE_CLASSIFIER_MODEL = "gpt-5-mini"
REASONING_EFFORT = "low"
NOTE_BATCH_SIZE = 100
MAX_NOTE_CLASSIFICATION_CALLS = 200
MAX_VERIFY_REQUESTS = 3
REQUEST_TIMEOUT_SECONDS = 30


# Keep repository and runtime paths in one explicit object.
@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    app_dir: Path
    docs_dir: Path
    data_dir: Path
    input_dir: Path
    sensors_dir: Path
    output_dir: Path
    logs_dir: Path
    cache_dir: Path
    operator_notes_cache_file: Path
    deterministic_findings_file: Path
    final_answer_file: Path
    run_report_file: Path


# Store secret-bearing Hub configuration away from reportable data.
@dataclass(frozen=True)
class HubConfig:
    api_key: str
    verify_url: str
    task_name: str = TASK_NAME


# Store OpenAI access and model settings for operator-note classification.
@dataclass(frozen=True)
class LlmConfig:
    api_key: str
    model_name: str
    reasoning_effort: str


# Store guard limits that keep local model and Hub usage bounded.
@dataclass(frozen=True)
class RuntimeConfig:
    note_batch_size: int
    max_note_classification_calls: int
    max_verify_requests: int
    request_timeout_seconds: int


# Keep all loaded configuration in one object passed through the app.
@dataclass(frozen=True)
class AppConfig:
    paths: AppPaths
    runtime: RuntimeConfig
    llm: LlmConfig | None
    hub: HubConfig | None


# Build stable repository-relative paths for the evaluation app.
def build_app_paths() -> AppPaths:
    app_dir = Path(__file__).resolve().parent
    repo_root = Path(__file__).resolve().parents[3]
    docs_dir = app_dir / "docs"
    data_dir = repo_root / "data" / "L11_evaluation"
    input_dir = data_dir / "input"
    sensors_dir = input_dir / "sensors"
    output_dir = data_dir / "output"
    logs_dir = data_dir / "logs"
    cache_dir = data_dir / "cache"

    return AppPaths(
        repo_root=repo_root,
        app_dir=app_dir,
        docs_dir=docs_dir,
        data_dir=data_dir,
        input_dir=input_dir,
        sensors_dir=sensors_dir,
        output_dir=output_dir,
        logs_dir=logs_dir,
        cache_dir=cache_dir,
        operator_notes_cache_file=cache_dir / "operator_notes_cache.json",
        deterministic_findings_file=output_dir / "deterministic_findings.json",
        final_answer_file=output_dir / "final_answer.json",
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


# Load Hub config only when a run is allowed to verify externally.
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
        model_name=NOTE_CLASSIFIER_MODEL,
        reasoning_effort=REASONING_EFFORT,
    )


# Load app-level guard settings.
def load_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        note_batch_size=NOTE_BATCH_SIZE,
        max_note_classification_calls=MAX_NOTE_CLASSIFICATION_CALLS,
        max_verify_requests=MAX_VERIFY_REQUESTS,
        request_timeout_seconds=REQUEST_TIMEOUT_SECONDS,
    )


# Load all app config while allowing local checks to skip secret-bearing config.
def load_app_config(
    *,
    require_hub: bool = True,
    require_llm: bool = True,
) -> AppConfig:
    return AppConfig(
        paths=build_app_paths(),
        runtime=load_runtime_config(),
        llm=load_llm_config(required=require_llm),
        hub=load_hub_config(required=require_hub),
    )


# Create local runtime directories before workflow steps write files.
def ensure_runtime_directories(paths: AppPaths) -> None:
    for path in (
        paths.data_dir,
        paths.input_dir,
        paths.output_dir,
        paths.logs_dir,
        paths.cache_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)


# Return a secret-safe summary for logs and setup diagnostics.
def build_safe_config_summary(config: AppConfig) -> dict[str, object]:
    return {
        "app": "L11_evaluation",
        "data_dir": str(config.paths.data_dir.relative_to(config.paths.repo_root)),
        "sensors_dir": str(config.paths.sensors_dir.relative_to(config.paths.repo_root)),
        "output_dir": str(config.paths.output_dir.relative_to(config.paths.repo_root)),
        "cache_dir": str(config.paths.cache_dir.relative_to(config.paths.repo_root)),
        "llm": {
            "loaded": config.llm is not None,
            "api_key": "configured" if config.llm else "not_loaded",
            "model_name": config.llm.model_name if config.llm else None,
            "reasoning_effort": config.llm.reasoning_effort if config.llm else None,
        },
        "runtime": {
            "note_batch_size": config.runtime.note_batch_size,
            "max_note_classification_calls": config.runtime.max_note_classification_calls,
            "max_verify_requests": config.runtime.max_verify_requests,
            "request_timeout_seconds": config.runtime.request_timeout_seconds,
        },
        "hub": {
            "loaded": config.hub is not None,
            "api_key": "configured" if config.hub else "not_loaded",
            "verify_url": "configured" if config.hub else "not_loaded",
            "task_name": config.hub.task_name if config.hub else TASK_NAME,
        },
    }
