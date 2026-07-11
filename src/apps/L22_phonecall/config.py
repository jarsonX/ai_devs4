# Configuration loading for the L22 phonecall workflow.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(dotenv_path=REPO_ROOT / ".env")

APP_NAME = "L22_phonecall"
TASK_NAME = "phonecall"

DEFAULT_STT_MODEL = "gpt-4o-transcribe"
DEFAULT_INTERPRETER_MODEL = "gpt-5-mini"
DEFAULT_PLANNER_MODEL = "gpt-5-mini"
DEFAULT_TTS_MODEL = "gpt-4o-mini-tts"
DEFAULT_TTS_VOICE = "coral"
DEFAULT_TTS_RESPONSE_FORMAT = "mp3"

DEFAULT_MAX_HUB_REQUESTS = 12
DEFAULT_MAX_STT_REQUESTS = 8
DEFAULT_MAX_INTERPRETER_REQUESTS = 10
DEFAULT_MAX_PLANNER_REQUESTS = 8
DEFAULT_MAX_TTS_REQUESTS = 8
DEFAULT_REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_MAX_UTTERANCE_WORDS = 28
OPERATOR_LANGUAGE = "pl"


# Keep repository and app runtime paths in one explicit object.
@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    app_dir: Path
    docs_dir: Path
    data_dir: Path
    calls_dir: Path
    output_dir: Path
    logs_dir: Path


# Store secret-bearing Hub configuration away from reportable data.
@dataclass(frozen=True)
class HubConfig:
    api_key: str
    verify_url: str
    task_name: str = TASK_NAME


# Store secret-bearing OpenAI configuration for model-backed steps.
@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    stt_model: str
    interpreter_model: str
    planner_model: str
    tts_model: str
    tts_voice: str
    tts_response_format: str


# Store runtime guardrails for one call attempt.
@dataclass(frozen=True)
class RuntimeConfig:
    max_hub_requests: int
    max_stt_requests: int
    max_interpreter_requests: int
    max_planner_requests: int
    max_tts_requests: int
    request_timeout_seconds: int
    max_utterance_words: int
    operator_language: str


# Keep all loaded configuration in one object passed through the app.
@dataclass(frozen=True)
class AppConfig:
    paths: AppPaths
    runtime: RuntimeConfig
    hub: HubConfig | None
    openai: OpenAIConfig | None


# Build stable repository-relative paths for the L22 app.
def build_app_paths() -> AppPaths:
    app_dir = Path(__file__).resolve().parent
    data_dir = REPO_ROOT / "data" / APP_NAME
    return AppPaths(
        repo_root=REPO_ROOT,
        app_dir=app_dir,
        docs_dir=app_dir / "docs",
        data_dir=data_dir,
        calls_dir=data_dir / "calls",
        output_dir=data_dir / "output",
        logs_dir=data_dir / "logs",
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


# Parse one optional integer environment variable with a lower bound.
def get_optional_int_env(name: str, default: int, minimum: int = 1) -> int:
    raw_value = get_optional_env(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer.") from error
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}.")
    return value


# Load Hub config only when real Hub calls are needed.
def load_hub_config(*, required: bool) -> HubConfig | None:
    if not required:
        return None
    return HubConfig(
        api_key=get_required_env("AI_DEVS_API_KEY"),
        verify_url=get_required_env("HUB_VERIFY_URL"),
    )


# Load OpenAI config only when model-backed calls are needed.
def load_openai_config(*, required: bool) -> OpenAIConfig | None:
    if not required:
        return None
    return OpenAIConfig(
        api_key=get_required_env("OPENAI_API_KEY"),
        stt_model=get_optional_env("L22_PHONECALL_STT_MODEL") or DEFAULT_STT_MODEL,
        interpreter_model=get_optional_env("L22_PHONECALL_INTERPRETER_MODEL")
        or DEFAULT_INTERPRETER_MODEL,
        planner_model=get_optional_env("L22_PHONECALL_PLANNER_MODEL") or DEFAULT_PLANNER_MODEL,
        tts_model=get_optional_env("L22_PHONECALL_TTS_MODEL") or DEFAULT_TTS_MODEL,
        tts_voice=get_optional_env("L22_PHONECALL_TTS_VOICE") or DEFAULT_TTS_VOICE,
        tts_response_format=get_optional_env("L22_PHONECALL_TTS_RESPONSE_FORMAT")
        or DEFAULT_TTS_RESPONSE_FORMAT,
    )


# Load runtime limits that keep Hub and model calls bounded.
def load_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        max_hub_requests=get_optional_int_env(
            "L22_PHONECALL_MAX_HUB_REQUESTS",
            DEFAULT_MAX_HUB_REQUESTS,
        ),
        max_stt_requests=get_optional_int_env(
            "L22_PHONECALL_MAX_STT_REQUESTS",
            DEFAULT_MAX_STT_REQUESTS,
        ),
        max_interpreter_requests=get_optional_int_env(
            "L22_PHONECALL_MAX_INTERPRETER_REQUESTS",
            DEFAULT_MAX_INTERPRETER_REQUESTS,
        ),
        max_planner_requests=get_optional_int_env(
            "L22_PHONECALL_MAX_PLANNER_REQUESTS",
            DEFAULT_MAX_PLANNER_REQUESTS,
        ),
        max_tts_requests=get_optional_int_env(
            "L22_PHONECALL_MAX_TTS_REQUESTS",
            DEFAULT_MAX_TTS_REQUESTS,
        ),
        request_timeout_seconds=get_optional_int_env(
            "L22_PHONECALL_REQUEST_TIMEOUT_SECONDS",
            DEFAULT_REQUEST_TIMEOUT_SECONDS,
        ),
        max_utterance_words=get_optional_int_env(
            "L22_PHONECALL_MAX_UTTERANCE_WORDS",
            DEFAULT_MAX_UTTERANCE_WORDS,
        ),
        operator_language=get_optional_env("L22_PHONECALL_OPERATOR_LANGUAGE") or OPERATOR_LANGUAGE,
    )


# Load app config while allowing dry runs to skip secret-bearing sections.
def load_app_config(
    *,
    require_hub: bool,
    require_openai: bool,
) -> AppConfig:
    return AppConfig(
        paths=build_app_paths(),
        runtime=load_runtime_config(),
        hub=load_hub_config(required=require_hub),
        openai=load_openai_config(required=require_openai),
    )


# Create runtime directories before workflow steps write files.
def ensure_runtime_directories(paths: AppPaths) -> None:
    for path in (
        paths.data_dir,
        paths.calls_dir,
        paths.output_dir,
        paths.logs_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)


# Return a secret-safe summary for local reports and dry-run output.
def build_safe_config_summary(config: AppConfig) -> dict[str, object]:
    return {
        "app": APP_NAME,
        "data_dir": str(config.paths.data_dir.relative_to(config.paths.repo_root)),
        "calls_dir": str(config.paths.calls_dir.relative_to(config.paths.repo_root)),
        "runtime": {
            "max_hub_requests": config.runtime.max_hub_requests,
            "max_stt_requests": config.runtime.max_stt_requests,
            "max_interpreter_requests": config.runtime.max_interpreter_requests,
            "max_planner_requests": config.runtime.max_planner_requests,
            "max_tts_requests": config.runtime.max_tts_requests,
            "request_timeout_seconds": config.runtime.request_timeout_seconds,
            "max_utterance_words": config.runtime.max_utterance_words,
            "operator_language": config.runtime.operator_language,
        },
        "hub": {
            "loaded": config.hub is not None,
            "api_key": "configured" if config.hub else "not_loaded",
            "verify_url": "configured" if config.hub else "not_loaded",
        },
        "openai": {
            "loaded": config.openai is not None,
            "api_key": "configured" if config.openai else "not_loaded",
            "stt_model": config.openai.stt_model if config.openai else DEFAULT_STT_MODEL,
            "interpreter_model": (
                config.openai.interpreter_model if config.openai else DEFAULT_INTERPRETER_MODEL
            ),
            "planner_model": config.openai.planner_model if config.openai else DEFAULT_PLANNER_MODEL,
            "tts_model": config.openai.tts_model if config.openai else DEFAULT_TTS_MODEL,
            "tts_voice": config.openai.tts_voice if config.openai else DEFAULT_TTS_VOICE,
            "tts_response_format": (
                config.openai.tts_response_format
                if config.openai
                else DEFAULT_TTS_RESPONSE_FORMAT
            ),
        },
    }
