# Configuration loading for the L21 radiomonitoring workflow.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(dotenv_path=REPO_ROOT / ".env")

APP_NAME = "L21_radiomonitoring"
TASK_NAME = "radiomonitoring"
DEFAULT_TEXT_MODEL = "gpt-5-mini"
DEFAULT_VISION_MODEL = "gpt-5.5"
DEFAULT_RESOLUTION_MODEL = "gpt-5-mini"
DEFAULT_AUDIO_MODEL = "whisper-1"
DEFAULT_MAX_LISTEN_REQUESTS = 40
DEFAULT_MAX_MODEL_REQUESTS = 20
DEFAULT_MAX_VERIFY_REQUESTS = 60
DEFAULT_MAX_MODEL_INPUT_CHARS = 12000
DEFAULT_MAX_IMAGE_PIXELS = 2_000_000
DEFAULT_MIN_RELEVANCE_SCORE_FOR_MODEL = 4
DEFAULT_REQUEST_TIMEOUT_SECONDS = 30


# Keep repository and app runtime paths in one explicit object.
@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    app_dir: Path
    docs_dir: Path
    data_dir: Path
    cache_dir: Path
    raw_signals_dir: Path
    attachments_dir: Path
    extracted_dir: Path
    output_dir: Path
    logs_dir: Path
    requests_ca_bundle_file: Path


# Store secret-bearing Hub configuration away from reportable data.
@dataclass(frozen=True)
class HubConfig:
    api_key: str
    verify_url: str
    task_name: str = TASK_NAME


# Store secret-bearing OpenAI configuration for extraction steps.
@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    text_model: str
    vision_model: str
    resolution_model: str
    audio_model: str


# Store guardrails and cheap-routing thresholds.
@dataclass(frozen=True)
class RuntimeConfig:
    max_listen_requests: int
    max_model_requests: int
    max_verify_requests: int
    max_model_input_chars: int
    max_image_pixels: int
    min_relevance_score_for_model: int
    request_timeout_seconds: int


# Keep all loaded configuration in one object passed through the app.
@dataclass(frozen=True)
class AppConfig:
    paths: AppPaths
    runtime: RuntimeConfig
    hub: HubConfig | None
    openai: OpenAIConfig | None


# Build stable repository-relative paths for the L21 app.
def build_app_paths() -> AppPaths:
    app_dir = Path(__file__).resolve().parent
    data_dir = REPO_ROOT / "data" / APP_NAME
    cache_dir = data_dir / "cache"
    return AppPaths(
        repo_root=REPO_ROOT,
        app_dir=app_dir,
        docs_dir=app_dir / "docs",
        data_dir=data_dir,
        cache_dir=cache_dir,
        raw_signals_dir=cache_dir / "raw_signals",
        attachments_dir=cache_dir / "attachments",
        extracted_dir=cache_dir / "extracted",
        output_dir=data_dir / "output",
        logs_dir=data_dir / "logs",
        requests_ca_bundle_file=REPO_ROOT
        / "data"
        / "L6_categorize"
        / "cache"
        / "requests_ca_bundle.pem",
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


# Load Hub config only when external Hub calls are needed.
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


# Load OpenAI config only when model calls are needed.
def load_openai_config(*, required: bool) -> OpenAIConfig | None:
    if not required and not get_optional_env("OPENAI_API_KEY"):
        return None
    return OpenAIConfig(
        api_key=get_required_env("OPENAI_API_KEY"),
        text_model=get_optional_env("L21_RADIOMONITORING_TEXT_MODEL") or DEFAULT_TEXT_MODEL,
        vision_model=get_optional_env("L21_RADIOMONITORING_VISION_MODEL") or DEFAULT_VISION_MODEL,
        resolution_model=get_optional_env("L21_RADIOMONITORING_RESOLUTION_MODEL")
        or DEFAULT_RESOLUTION_MODEL,
        audio_model=get_optional_env("L21_RADIOMONITORING_AUDIO_MODEL") or DEFAULT_AUDIO_MODEL,
    )


# Load runtime limits that keep external and model calls bounded.
def load_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        max_listen_requests=get_optional_int_env(
            "L21_RADIOMONITORING_MAX_LISTEN_REQUESTS",
            DEFAULT_MAX_LISTEN_REQUESTS,
        ),
        max_model_requests=get_optional_int_env(
            "L21_RADIOMONITORING_MAX_MODEL_REQUESTS",
            DEFAULT_MAX_MODEL_REQUESTS,
        ),
        max_verify_requests=get_optional_int_env(
            "L21_RADIOMONITORING_MAX_VERIFY_REQUESTS",
            DEFAULT_MAX_VERIFY_REQUESTS,
        ),
        max_model_input_chars=get_optional_int_env(
            "L21_RADIOMONITORING_MAX_MODEL_INPUT_CHARS",
            DEFAULT_MAX_MODEL_INPUT_CHARS,
        ),
        max_image_pixels=get_optional_int_env(
            "L21_RADIOMONITORING_MAX_IMAGE_PIXELS",
            DEFAULT_MAX_IMAGE_PIXELS,
        ),
        min_relevance_score_for_model=get_optional_int_env(
            "L21_RADIOMONITORING_MIN_RELEVANCE_SCORE_FOR_MODEL",
            DEFAULT_MIN_RELEVANCE_SCORE_FOR_MODEL,
            minimum=0,
        ),
        request_timeout_seconds=get_optional_int_env(
            "L21_RADIOMONITORING_REQUEST_TIMEOUT_SECONDS",
            DEFAULT_REQUEST_TIMEOUT_SECONDS,
        ),
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
        paths.cache_dir,
        paths.raw_signals_dir,
        paths.attachments_dir,
        paths.extracted_dir,
        paths.output_dir,
        paths.logs_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)


# Apply repository TLS setup before real external API calls.
def prepare_tls_environment(paths: AppPaths, *, required: bool = True) -> None:
    bundle_path = paths.requests_ca_bundle_file
    if not bundle_path.exists():
        if required:
            raise ValueError(
                "TLS CA bundle file is missing. Expected "
                f"{bundle_path.relative_to(paths.repo_root)}."
            )
        return
    bundle = str(bundle_path.resolve())
    os.environ["REQUESTS_CA_BUNDLE"] = bundle
    os.environ["SSL_CERT_FILE"] = bundle


# Return a secret-safe summary for local reports.
def build_safe_config_summary(config: AppConfig) -> dict[str, object]:
    return {
        "app": APP_NAME,
        "data_dir": str(config.paths.data_dir.relative_to(config.paths.repo_root)),
        "output_dir": str(config.paths.output_dir.relative_to(config.paths.repo_root)),
        "runtime": {
            "max_listen_requests": config.runtime.max_listen_requests,
            "max_model_requests": config.runtime.max_model_requests,
            "max_verify_requests": config.runtime.max_verify_requests,
            "max_model_input_chars": config.runtime.max_model_input_chars,
            "max_image_pixels": config.runtime.max_image_pixels,
            "min_relevance_score_for_model": config.runtime.min_relevance_score_for_model,
            "request_timeout_seconds": config.runtime.request_timeout_seconds,
        },
        "hub": {
            "loaded": config.hub is not None,
            "api_key": "configured" if config.hub else "not_loaded",
            "verify_url": "configured" if config.hub else "not_loaded",
            "task_name": config.hub.task_name if config.hub else TASK_NAME,
        },
        "openai": {
            "loaded": config.openai is not None,
            "api_key": "configured" if config.openai else "not_loaded",
            "text_model": config.openai.text_model if config.openai else None,
            "vision_model": config.openai.vision_model if config.openai else None,
            "resolution_model": config.openai.resolution_model if config.openai else None,
            "audio_model": config.openai.audio_model if config.openai else None,
        },
    }
