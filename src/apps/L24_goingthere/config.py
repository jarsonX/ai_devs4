# Configuration and runtime paths for the L24 goingthere app.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(REPO_ROOT / ".env")

APP_NAME = "L24_goingthere"
TASK_NAME = "goingthere"
REQUEST_TIMEOUT_SECONDS = 30
MAX_TOTAL_REQUESTS = 120
MAX_OPERATION_ATTEMPTS = 8
BASE_BACKOFF_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 12.0
DEFAULT_RADIO_MODEL = "gpt-5.6-luna"
DEFAULT_REASONING_EFFORT = "low"
MAX_MODEL_REQUESTS = 15
MAX_HINT_CHARACTERS = 2_000


# Keep secret-bearing Hub settings separate from reportable configuration.
@dataclass(frozen=True)
class HubConfig:
    api_key: str
    verify_url: str
    task_name: str = TASK_NAME

    # Derive the shared course API base without duplicating an operational URL.
    @property
    def base_url(self) -> str:
        return self.verify_url.rsplit("/", 1)[0]


# Keep secret-bearing OpenAI settings separate from reportable runtime settings.
@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    model: str = DEFAULT_RADIO_MODEL
    reasoning_effort: str = DEFAULT_REASONING_EFFORT


# Keep repository and runtime paths in one explicit object.
@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    output_dir: Path
    logs_dir: Path
    requests_ca_bundle_file: Path


# Keep retry and request guards in one immutable object.
@dataclass(frozen=True)
class RuntimeConfig:
    request_timeout_seconds: int = REQUEST_TIMEOUT_SECONDS
    max_total_requests: int = MAX_TOTAL_REQUESTS
    max_operation_attempts: int = MAX_OPERATION_ATTEMPTS
    base_backoff_seconds: float = BASE_BACKOFF_SECONDS
    max_backoff_seconds: float = MAX_BACKOFF_SECONDS
    max_model_requests: int = MAX_MODEL_REQUESTS
    max_hint_characters: int = MAX_HINT_CHARACTERS


# Return one required environment value or fail before a network call.
def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing.")
    return value


# Build stable repository-relative runtime paths.
def build_paths() -> AppPaths:
    data_dir = REPO_ROOT / "data" / APP_NAME
    return AppPaths(
        repo_root=REPO_ROOT,
        output_dir=data_dir / "output",
        logs_dir=data_dir / "logs",
        requests_ca_bundle_file=(
            REPO_ROOT / "data" / "L6_categorize" / "cache" / "requests_ca_bundle.pem"
        ),
    )


# Load Hub settings only for an explicitly requested live run.
def load_hub_config() -> HubConfig:
    return HubConfig(
        api_key=get_required_env("AI_DEVS_API_KEY"),
        verify_url=get_required_env("HUB_VERIFY_URL"),
    )


# Load the existing OpenAI credential only for a model-powered mode.
def load_openai_config() -> OpenAIConfig:
    return OpenAIConfig(api_key=get_required_env("OPENAI_API_KEY"))


# Apply the repository CA bundle while keeping TLS verification enabled.
def prepare_tls_environment(paths: AppPaths) -> None:
    if not paths.requests_ca_bundle_file.exists():
        raise ValueError("The repository TLS CA bundle is missing.")
    bundle = str(paths.requests_ca_bundle_file.resolve())
    os.environ["REQUESTS_CA_BUNDLE"] = bundle
    os.environ["SSL_CERT_FILE"] = bundle
