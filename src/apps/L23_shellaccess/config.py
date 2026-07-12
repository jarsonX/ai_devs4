# Configuration and runtime paths for the L23 shellaccess app.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(REPO_ROOT / ".env")

APP_NAME = "L23_shellaccess"
TASK_NAME = "shellaccess"
REQUEST_TIMEOUT_SECONDS = 30
MAX_VERIFY_REQUESTS = 6


# Keep secret-bearing Hub settings separate from reportable configuration.
@dataclass(frozen=True)
class HubConfig:
    api_key: str
    verify_url: str
    task_name: str = TASK_NAME


# Keep repository and runtime paths in one explicit object.
@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    output_dir: Path
    requests_ca_bundle_file: Path


# Return one required environment value or fail before a network call.
def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing.")
    return value


# Build stable repository-relative runtime paths.
def build_paths() -> AppPaths:
    return AppPaths(
        repo_root=REPO_ROOT,
        output_dir=REPO_ROOT / "data" / APP_NAME / "output",
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


# Apply the repository CA bundle while keeping TLS verification enabled.
def prepare_tls_environment(paths: AppPaths) -> None:
    if not paths.requests_ca_bundle_file.exists():
        raise ValueError("The repository TLS CA bundle is missing.")
    bundle = str(paths.requests_ca_bundle_file.resolve())
    os.environ["REQUESTS_CA_BUNDLE"] = bundle
    os.environ["SSL_CERT_FILE"] = bundle
