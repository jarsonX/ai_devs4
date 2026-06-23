# Configuration loading for the deterministic L18 Domatowo controller.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

APP_NAME = "L18_domatowo"
TASK_NAME = "domatowo"
DEFAULT_HUB_VERIFY_URL = "https://hub.ag3nts.org/verify"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_MAX_REQUESTS = 120
ACTION_POINT_LIMIT = 300
TRANSPORTER_LIMIT = 4
SCOUT_LIMIT = 8
TLS_CA_BUNDLE = Path("data") / "L6_categorize" / "cache" / "requests_ca_bundle.pem"


# Keep repository and runtime paths in one explicit object.
@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    app_dir: Path
    docs_dir: Path
    data_dir: Path
    logs_dir: Path
    output_dir: Path


# Store secret-bearing Hub configuration away from reportable data.
@dataclass(frozen=True)
class HubConfig:
    api_key: str
    verify_url: str
    task_name: str = TASK_NAME


# Store deterministic operation limits for the live workflow.
@dataclass(frozen=True)
class RuntimeConfig:
    request_timeout_seconds: int
    max_requests: int
    action_point_limit: int
    transporter_limit: int
    scout_limit: int


# Keep all app settings in one object passed through the workflow.
@dataclass(frozen=True)
class AppConfig:
    paths: AppPaths
    hub: HubConfig | None
    runtime: RuntimeConfig


# Read one required environment variable and fail with a clear setup error.
def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing.")
    return value


# Read one optional environment variable and normalize empty strings.
def get_optional_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


# Read an integer environment override while keeping a clear fallback.
def get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        return int(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer.") from error


# Build stable repository-relative paths for runtime data.
def build_app_paths() -> AppPaths:
    app_dir = Path(__file__).resolve().parent
    repo_root = Path(__file__).resolve().parents[3]
    data_dir = repo_root / "data" / APP_NAME
    return AppPaths(
        repo_root=repo_root,
        app_dir=app_dir,
        docs_dir=app_dir / "docs",
        data_dir=data_dir,
        logs_dir=data_dir / "logs",
        output_dir=data_dir / "output",
    )


# Apply the repository CA bundle setup when the local bundle exists.
def prepare_tls_environment(paths: AppPaths, *, required: bool = False) -> bool:
    bundle_path = paths.repo_root / TLS_CA_BUNDLE
    if not bundle_path.exists():
        if required:
            raise FileNotFoundError(f"TLS CA bundle is missing: {bundle_path}")
        return False
    resolved_bundle = str(bundle_path.resolve())
    os.environ["REQUESTS_CA_BUNDLE"] = resolved_bundle
    os.environ["SSL_CERT_FILE"] = resolved_bundle
    return True


# Load Hub settings only when a real submit run needs them.
def load_hub_config(*, required: bool) -> HubConfig | None:
    if not required and not get_optional_env("AI_DEVS_API_KEY"):
        return None
    return HubConfig(
        api_key=get_required_env("AI_DEVS_API_KEY"),
        verify_url=get_optional_env("HUB_VERIFY_URL") or DEFAULT_HUB_VERIFY_URL,
    )


# Load local runtime guard settings.
def load_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        request_timeout_seconds=get_int_env(
            "L18_REQUEST_TIMEOUT_SECONDS",
            DEFAULT_REQUEST_TIMEOUT_SECONDS,
        ),
        max_requests=get_int_env("L18_MAX_REQUESTS", DEFAULT_MAX_REQUESTS),
        action_point_limit=ACTION_POINT_LIMIT,
        transporter_limit=TRANSPORTER_LIMIT,
        scout_limit=SCOUT_LIMIT,
    )


# Load all configuration needed for the selected CLI mode.
def load_app_config(*, require_hub: bool = True) -> AppConfig:
    return AppConfig(
        paths=build_app_paths(),
        hub=load_hub_config(required=require_hub),
        runtime=load_runtime_config(),
    )


# Create runtime directories before logs or reports are written.
def ensure_runtime_directories(paths: AppPaths) -> None:
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    paths.output_dir.mkdir(parents=True, exist_ok=True)


# Return a secret-safe summary for config checks.
def build_safe_config_summary(config: AppConfig) -> dict[str, object]:
    return {
        "app": APP_NAME,
        "data_dir": str(config.paths.data_dir.relative_to(config.paths.repo_root)),
        "hub": {
            "loaded": config.hub is not None,
            "api_key": "configured" if config.hub else "not_loaded",
            "verify_url": "configured" if config.hub else "not_loaded",
        },
        "runtime": {
            "request_timeout_seconds": config.runtime.request_timeout_seconds,
            "max_requests": config.runtime.max_requests,
            "action_point_limit": config.runtime.action_point_limit,
            "transporter_limit": config.runtime.transporter_limit,
            "scout_limit": config.runtime.scout_limit,
        },
    }
