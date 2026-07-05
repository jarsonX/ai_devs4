# Configuration loading for the L17 windpower workflow.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(dotenv_path=REPO_ROOT / ".env")

APP_NAME = "L17_windpower"
TASK_NAME = "windpower"
REQUEST_TIMEOUT_SECONDS = 20
SERVICE_WINDOW_SECONDS = 40
LOCAL_DEADLINE_SECONDS = 38
POLL_INTERVAL_SECONDS = 0.4
MAX_HUB_REQUESTS = 120


# Keep repository and runtime paths in one explicit object.
@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    app_dir: Path
    docs_dir: Path
    data_dir: Path
    logs_dir: Path
    output_dir: Path
    requests_ca_bundle_file: Path


# Store secret-bearing Hub configuration away from reportable data.
@dataclass(frozen=True)
class HubConfig:
    api_key: str
    verify_url: str
    task_name: str = TASK_NAME


# Store stable runtime guard values in one object.
@dataclass(frozen=True)
class RuntimeConfig:
    request_timeout_seconds: int
    service_window_seconds: int
    local_deadline_seconds: int
    poll_interval_seconds: float
    max_hub_requests: int


# Keep all loaded configuration in one object passed through the app.
@dataclass(frozen=True)
class AppConfig:
    paths: AppPaths
    hub: HubConfig | None
    runtime: RuntimeConfig


# Build stable repository-relative paths for the L17 app.
def build_app_paths() -> AppPaths:
    app_dir = Path(__file__).resolve().parent
    docs_dir = app_dir / "docs"
    data_dir = REPO_ROOT / "data" / APP_NAME

    return AppPaths(
        repo_root=REPO_ROOT,
        app_dir=app_dir,
        docs_dir=docs_dir,
        data_dir=data_dir,
        logs_dir=data_dir / "logs",
        output_dir=data_dir / "output",
        requests_ca_bundle_file=REPO_ROOT / "data" / "L6_categorize" / "cache" / "requests_ca_bundle.pem",
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


# Load Hub config only when a run is allowed to call the external API.
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


# Load app-level guard settings.
def load_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        request_timeout_seconds=REQUEST_TIMEOUT_SECONDS,
        service_window_seconds=SERVICE_WINDOW_SECONDS,
        local_deadline_seconds=LOCAL_DEADLINE_SECONDS,
        poll_interval_seconds=POLL_INTERVAL_SECONDS,
        max_hub_requests=MAX_HUB_REQUESTS,
    )


# Load all app config while allowing tests and config checks to skip secrets.
def load_app_config(*, require_hub: bool = True) -> AppConfig:
    return AppConfig(
        paths=build_app_paths(),
        hub=load_hub_config(required=require_hub),
        runtime=load_runtime_config(),
    )


# Create local runtime directories before workflow steps write files.
def ensure_runtime_directories(paths: AppPaths) -> None:
    for path in (paths.data_dir, paths.logs_dir, paths.output_dir):
        path.mkdir(parents=True, exist_ok=True)


# Apply the repository TLS setup before any real external API call.
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


# Return a secret-safe summary for logs and setup diagnostics.
def build_safe_config_summary(config: AppConfig) -> dict[str, object]:
    return {
        "app": APP_NAME,
        "data_dir": str(config.paths.data_dir.relative_to(config.paths.repo_root)),
        "logs_dir": str(config.paths.logs_dir.relative_to(config.paths.repo_root)),
        "output_dir": str(config.paths.output_dir.relative_to(config.paths.repo_root)),
        "runtime": {
            "request_timeout_seconds": config.runtime.request_timeout_seconds,
            "service_window_seconds": config.runtime.service_window_seconds,
            "local_deadline_seconds": config.runtime.local_deadline_seconds,
            "poll_interval_seconds": config.runtime.poll_interval_seconds,
            "max_hub_requests": config.runtime.max_hub_requests,
        },
        "hub": {
            "loaded": config.hub is not None,
            "api_key": "configured" if config.hub else "not_loaded",
            "verify_url": "configured" if config.hub else "not_loaded",
            "task_name": config.hub.task_name if config.hub else TASK_NAME,
        },
    }
