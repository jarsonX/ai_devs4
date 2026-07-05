# Configuration loading for the L16 okoeditor workflow.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(dotenv_path=REPO_ROOT / ".env")

TASK_NAME = "okoeditor"
REQUEST_TIMEOUT_SECONDS = 30
MAX_PAGE_FETCHES = 32
MAX_PLANNED_WRITES = 3


# Keep repository and runtime paths in one explicit object.
@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    app_dir: Path
    docs_dir: Path
    data_dir: Path
    cache_dir: Path
    logs_dir: Path
    output_dir: Path
    requests_ca_bundle_file: Path


# Store secret-bearing verify API configuration away from reportable data.
@dataclass(frozen=True)
class VerifyApiConfig:
    api_key: str
    verify_url: str
    task_name: str = TASK_NAME


# Store secret-bearing OKO session configuration away from reportable data.
@dataclass(frozen=True)
class OkoWebConfig:
    base_url: str
    operator_login: str
    operator_password: str
    access_key: str


# Store stable runtime guard values in one object.
@dataclass(frozen=True)
class RuntimeConfig:
    request_timeout_seconds: int
    max_page_fetches: int
    max_planned_writes: int


# Keep all loaded configuration in one object passed through the app.
@dataclass(frozen=True)
class AppConfig:
    paths: AppPaths
    verify_api: VerifyApiConfig | None
    oko_web: OkoWebConfig | None
    runtime: RuntimeConfig


# Build stable repository-relative paths for the L16 app.
def build_app_paths() -> AppPaths:
    app_dir = Path(__file__).resolve().parent
    docs_dir = app_dir / "docs"
    data_dir = REPO_ROOT / "data" / "L16_okoeditor"
    cache_dir = data_dir / "cache"
    logs_dir = data_dir / "logs"
    output_dir = data_dir / "output"

    return AppPaths(
        repo_root=REPO_ROOT,
        app_dir=app_dir,
        docs_dir=docs_dir,
        data_dir=data_dir,
        cache_dir=cache_dir,
        logs_dir=logs_dir,
        output_dir=output_dir,
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


# Load verify API config only when a run is allowed to call the external API.
def load_verify_api_config(*, required: bool) -> VerifyApiConfig | None:
    if (
        not required
        and not get_optional_env("AI_DEVS_API_KEY")
        and not get_optional_env("HUB_VERIFY_URL")
    ):
        return None

    return VerifyApiConfig(
        api_key=get_required_env("AI_DEVS_API_KEY"),
        verify_url=get_required_env("HUB_VERIFY_URL"),
    )


# Load OKO web config only when a run is allowed to use the external session.
def load_oko_web_config(*, required: bool) -> OkoWebConfig | None:
    if (
        not required
        and not get_optional_env("AI_DEVS_API_KEY")
        and not get_optional_env("OKO_BASE_URL")
        and not get_optional_env("OKO_OPERATOR_LOGIN")
        and not get_optional_env("OKO_OPERATOR_PASSWORD")
    ):
        return None

    return OkoWebConfig(
        base_url=get_required_env("OKO_BASE_URL").rstrip("/") + "/",
        operator_login=get_required_env("OKO_OPERATOR_LOGIN"),
        operator_password=get_required_env("OKO_OPERATOR_PASSWORD"),
        access_key=get_required_env("AI_DEVS_API_KEY"),
    )


# Load app-level guard settings.
def load_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        request_timeout_seconds=REQUEST_TIMEOUT_SECONDS,
        max_page_fetches=MAX_PAGE_FETCHES,
        max_planned_writes=MAX_PLANNED_WRITES,
    )


# Load all app config while allowing tests to skip secret-bearing config.
def load_app_config(
    *,
    require_verify_api: bool = True,
    require_oko_web: bool = True,
) -> AppConfig:
    return AppConfig(
        paths=build_app_paths(),
        verify_api=load_verify_api_config(required=require_verify_api),
        oko_web=load_oko_web_config(required=require_oko_web),
        runtime=load_runtime_config(),
    )


# Create local runtime directories before workflow steps write files.
def ensure_runtime_directories(paths: AppPaths) -> None:
    for path in (paths.data_dir, paths.cache_dir, paths.logs_dir, paths.output_dir):
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
        "app": "L16_okoeditor",
        "data_dir": str(config.paths.data_dir.relative_to(config.paths.repo_root)),
        "cache_dir": str(config.paths.cache_dir.relative_to(config.paths.repo_root)),
        "logs_dir": str(config.paths.logs_dir.relative_to(config.paths.repo_root)),
        "output_dir": str(config.paths.output_dir.relative_to(config.paths.repo_root)),
        "runtime": {
            "request_timeout_seconds": config.runtime.request_timeout_seconds,
            "max_page_fetches": config.runtime.max_page_fetches,
            "max_planned_writes": config.runtime.max_planned_writes,
        },
        "verify_api": {
            "loaded": config.verify_api is not None,
            "api_key": "configured" if config.verify_api else "not_loaded",
            "verify_url": "configured" if config.verify_api else "not_loaded",
        },
        "oko_web": {
            "loaded": config.oko_web is not None,
            "base_url": "configured" if config.oko_web else "not_loaded",
            "operator_login": "configured" if config.oko_web else "not_loaded",
            "operator_password": "configured" if config.oko_web else "not_loaded",
            "access_key": "configured" if config.oko_web else "not_loaded",
        },
    }
