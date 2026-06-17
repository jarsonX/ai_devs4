# This module keeps local runtime paths and server defaults for L14_negotiations.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


TASK_NAME = "negotiations"
APP_NAME = "L14_negotiations"
DEFAULT_APP_HOST = "127.0.0.1"
DEFAULT_APP_PORT = 3014
DEFAULT_MAX_REQUEST_BYTES = 8_192
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
DEFAULT_REASONING_EFFORT = "none"
DEFAULT_INTERPRETER_MAX_INPUT_CHARS = 1_000
DEFAULT_INTERPRETER_MAX_OUTPUT_TOKENS = 600
DEFAULT_INTERPRETER_RETRY_LIMIT = 1
DEFAULT_HUB_REQUEST_TIMEOUT_SECONDS = 30
TLS_CA_BUNDLE = Path("data") / "L6_categorize" / "cache" / "requests_ca_bundle.pem"


# Group repository-relative paths used by the app.
@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    app_dir: Path
    data_dir: Path
    input_dir: Path
    output_dir: Path
    logs_dir: Path
    cities_csv: Path
    items_csv: Path
    connections_csv: Path


# Store local server settings that are safe to print.
@dataclass(frozen=True)
class ServerConfig:
    host: str
    port: int
    max_request_bytes: int


# Store LLM interpreter settings separately so local data checks do not need secrets.
@dataclass(frozen=True)
class LlmConfig:
    api_key: str
    model: str
    reasoning_effort: str
    max_input_chars: int
    max_output_tokens: int
    retry_limit: int


# Store secret-bearing Hub configuration away from reportable data.
@dataclass(frozen=True)
class HubConfig:
    api_key: str
    verify_url: str
    task_name: str = TASK_NAME
    request_timeout_seconds: int = DEFAULT_HUB_REQUEST_TIMEOUT_SECONDS


# Keep local app configuration in one object.
@dataclass(frozen=True)
class AppConfig:
    paths: AppPaths
    server: ServerConfig
    task_name: str = TASK_NAME


# Read an integer environment override while keeping a clear fallback.
def get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        return int(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer.") from error


# Read one required environment variable and fail with a clear setup error.
def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing.")
    return value


# Build stable repository and data paths without requiring secrets.
def build_app_paths() -> AppPaths:
    app_dir = Path(__file__).resolve().parent
    repo_root = Path(__file__).resolve().parents[3]
    data_dir = repo_root / "data" / APP_NAME
    input_dir = data_dir / "input"
    return AppPaths(
        repo_root=repo_root,
        app_dir=app_dir,
        data_dir=data_dir,
        input_dir=input_dir,
        output_dir=data_dir / "output",
        logs_dir=data_dir / "logs",
        cities_csv=input_dir / "cities.csv",
        items_csv=input_dir / "items.csv",
        connections_csv=input_dir / "connections.csv",
    )


# Apply the repository CA bundle setup before real OpenAI or Hub calls.
def apply_repository_tls_ca_setup(paths: AppPaths | None = None) -> bool:
    app_paths = paths or build_app_paths()
    bundle_path = app_paths.repo_root / TLS_CA_BUNDLE
    if not bundle_path.exists():
        return False
    resolved_bundle = str(bundle_path.resolve())
    os.environ["REQUESTS_CA_BUNDLE"] = resolved_bundle
    os.environ["SSL_CERT_FILE"] = resolved_bundle
    return True


# Load non-secret settings needed to start the local app skeleton.
def get_config() -> AppConfig:
    return AppConfig(
        paths=build_app_paths(),
        server=ServerConfig(
            host=os.getenv("HOST", DEFAULT_APP_HOST).strip() or DEFAULT_APP_HOST,
            port=get_int_env("PORT", DEFAULT_APP_PORT),
            max_request_bytes=get_int_env(
                "MAX_REQUEST_BYTES",
                DEFAULT_MAX_REQUEST_BYTES,
            ),
        ),
    )


# Load the approved LLM interpreter settings only when the interpreter is used.
def get_llm_config() -> LlmConfig:
    return LlmConfig(
        api_key=get_required_env("OPENAI_API_KEY"),
        model=DEFAULT_OPENAI_MODEL,
        reasoning_effort=DEFAULT_REASONING_EFFORT,
        max_input_chars=DEFAULT_INTERPRETER_MAX_INPUT_CHARS,
        max_output_tokens=DEFAULT_INTERPRETER_MAX_OUTPUT_TOKENS,
        retry_limit=DEFAULT_INTERPRETER_RETRY_LIMIT,
    )


# Load Hub verification settings only for explicit registration or check commands.
def get_hub_config() -> HubConfig:
    return HubConfig(
        api_key=get_required_env("AI_DEVS_API_KEY"),
        verify_url=get_required_env("HUB_VERIFY_URL"),
        request_timeout_seconds=get_int_env(
            "HUB_REQUEST_TIMEOUT_SECONDS",
            DEFAULT_HUB_REQUEST_TIMEOUT_SECONDS,
        ),
    )


# Create ignored runtime directories before writing logs or Hub responses.
def ensure_runtime_directories(config: AppConfig) -> None:
    config.paths.output_dir.mkdir(parents=True, exist_ok=True)
    config.paths.logs_dir.mkdir(parents=True, exist_ok=True)
