# Configuration loading for the L19 filesystem workflow.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(dotenv_path=REPO_ROOT / ".env")

APP_NAME = "L19_filesystem"
TASK_NAME = "filesystem"
DEFAULT_VERIFY_URL = "h" + "ttps://" + "hub." + "ag3nts." + "org" + "/verify"
REQUEST_TIMEOUT_SECONDS = 30
MAX_VERIFY_REQUESTS = 8


# Keep repository and runtime paths in one explicit object.
@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    app_dir: Path
    docs_dir: Path
    data_dir: Path
    input_dir: Path
    output_dir: Path
    logs_dir: Path
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
    max_verify_requests: int


# Keep all loaded configuration in one object passed through the app.
@dataclass(frozen=True)
class AppConfig:
    paths: AppPaths
    hub: HubConfig | None
    runtime: RuntimeConfig


# Build stable repository-relative paths for the L19 app.
def build_app_paths() -> AppPaths:
    app_dir = Path(__file__).resolve().parent
    data_dir = REPO_ROOT / "data" / APP_NAME

    return AppPaths(
        repo_root=REPO_ROOT,
        app_dir=app_dir,
        docs_dir=app_dir / "docs",
        data_dir=data_dir,
        input_dir=data_dir / "input",
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


# Load Hub config only when a run is allowed to call the external API.
def load_hub_config(*, required: bool) -> HubConfig | None:
    if not required and not get_optional_env("AI_DEVS_API_KEY"):
        return None

    return HubConfig(
        api_key=get_required_env("AI_DEVS_API_KEY"),
        verify_url=get_optional_env("HUB_VERIFY_URL") or DEFAULT_VERIFY_URL,
    )


# Load app-level guard settings.
def load_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        request_timeout_seconds=REQUEST_TIMEOUT_SECONDS,
        max_verify_requests=MAX_VERIFY_REQUESTS,
    )


# Load all app config while allowing dry runs to skip secret-bearing config.
def load_app_config(*, require_hub: bool = False) -> AppConfig:
    return AppConfig(
        paths=build_app_paths(),
        hub=load_hub_config(required=require_hub),
        runtime=load_runtime_config(),
    )


# Create local runtime directories before workflow steps write files.
def ensure_runtime_directories(paths: AppPaths) -> None:
    for path in (paths.data_dir, paths.output_dir, paths.logs_dir):
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
        "output_dir": str(config.paths.output_dir.relative_to(config.paths.repo_root)),
        "logs_dir": str(config.paths.logs_dir.relative_to(config.paths.repo_root)),
        "runtime": {
            "request_timeout_seconds": config.runtime.request_timeout_seconds,
            "max_verify_requests": config.runtime.max_verify_requests,
        },
        "hub": {
            "loaded": config.hub is not None,
            "api_key": "configured" if config.hub else "not_loaded",
            "verify_url": "configured" if config.hub else "not_loaded",
            "task_name": config.hub.task_name if config.hub else TASK_NAME,
        },
    }
