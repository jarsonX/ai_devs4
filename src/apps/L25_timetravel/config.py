# Configuration, safety limits, and runtime paths for L25 timetravel.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(REPO_ROOT / ".env")

APP_NAME = "L25_timetravel"
TASK_NAME = "timetravel"
DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_REASONING_EFFORT = "low"
REQUEST_TIMEOUT_SECONDS = 30
MAX_HUB_REQUESTS = 120
MAX_MODEL_REQUESTS_PER_AGENT = 30
MAX_TOOL_STEPS_PER_AGENT = 80
MAX_MODEL_OUTPUT_TOKENS = 256
MAX_HINT_CHARACTERS = 2_000
MODE_WAIT_TIMEOUT_SECONDS = 35
POLL_INTERVAL_SECONDS = 0.35
POST_WRITE_SETTLE_SECONDS = 2.3
ACTIVATION_LEASE_SECONDS = 1.5
MAX_SNAPSHOT_AGE_SECONDS = 1.25


# Keep Hub credentials and endpoint together without logging their values.
@dataclass(frozen=True)
class HubConfig:
    api_key: str
    verify_url: str
    task_name: str = TASK_NAME


# Keep OpenAI credentials separate from ordinary runtime settings.
@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    model: str = DEFAULT_MODEL
    reasoning_effort: str = DEFAULT_REASONING_EFFORT


# Keep Easytools credentials and the approved preview URL together.
@dataclass(frozen=True)
class BrowserConfig:
    email: str
    password: str
    preview_url: str
    channel: str = "msedge"
    headless: bool = True


# Keep all repository and runtime paths explicit.
@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    app_data_dir: Path
    input_doc: Path
    runs_dir: Path
    output_dir: Path
    logs_dir: Path
    requests_ca_bundle_file: Path


# Keep ordinary limits immutable and injectable in tests.
@dataclass(frozen=True)
class RuntimeConfig:
    request_timeout_seconds: int = REQUEST_TIMEOUT_SECONDS
    max_hub_requests: int = MAX_HUB_REQUESTS
    max_model_requests_per_agent: int = MAX_MODEL_REQUESTS_PER_AGENT
    max_tool_steps_per_agent: int = MAX_TOOL_STEPS_PER_AGENT
    max_model_output_tokens: int = MAX_MODEL_OUTPUT_TOKENS
    max_hint_characters: int = MAX_HINT_CHARACTERS
    mode_wait_timeout_seconds: int = MODE_WAIT_TIMEOUT_SECONDS
    poll_interval_seconds: float = POLL_INTERVAL_SECONDS
    post_write_settle_seconds: float = POST_WRITE_SETTLE_SECONDS
    activation_lease_seconds: float = ACTIVATION_LEASE_SECONDS
    max_snapshot_age_seconds: float = MAX_SNAPSHOT_AGE_SECONDS


# Return one required environment value or fail before external work starts.
def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing.")
    return value


# Build stable repository-relative application paths.
def build_paths() -> AppPaths:
    app_data_dir = REPO_ROOT / "data" / APP_NAME
    return AppPaths(
        repo_root=REPO_ROOT,
        app_data_dir=app_data_dir,
        input_doc=app_data_dir / "input" / "timetravel.md",
        runs_dir=app_data_dir / "runs",
        output_dir=app_data_dir / "output",
        logs_dir=app_data_dir / "logs",
        requests_ca_bundle_file=(
            REPO_ROOT / "data" / "L6_categorize" / "cache" / "requests_ca_bundle.pem"
        ),
    )


# Load Hub secrets only for a mode that needs real Hub access.
def load_hub_config() -> HubConfig:
    return HubConfig(
        api_key=get_required_env("AI_DEVS_API_KEY"),
        verify_url=get_required_env("HUB_VERIFY_URL"),
    )


# Load the existing OpenAI key only for a model-powered mode.
def load_openai_config() -> OpenAIConfig:
    return OpenAIConfig(api_key=get_required_env("OPENAI_API_KEY"))


# Load browser credentials only for authenticated preview use.
def load_browser_config() -> BrowserConfig:
    explicit_preview = os.getenv("TIMETRAVEL_PREVIEW_URL", "").strip()
    hub_base = os.getenv("HUB_BASE_URL", "").strip()
    if not explicit_preview and not hub_base:
        raise ValueError("TIMETRAVEL_PREVIEW_URL or HUB_BASE_URL is missing.")
    preview_url = explicit_preview or f"{hub_base.rstrip('/')}/timetravel_preview"
    return BrowserConfig(
        email=get_required_env("EASYTOOLS_EMAIL"),
        password=get_required_env("EASYTOOLS_PASSWORD"),
        preview_url=preview_url,
    )


# Apply the repository CA bundle while keeping TLS verification enabled.
def prepare_tls_environment(paths: AppPaths) -> None:
    if not paths.requests_ca_bundle_file.exists():
        raise ValueError("The repository TLS CA bundle is missing.")
    bundle = str(paths.requests_ca_bundle_file.resolve())
    os.environ["REQUESTS_CA_BUNDLE"] = bundle
    os.environ["SSL_CERT_FILE"] = bundle
