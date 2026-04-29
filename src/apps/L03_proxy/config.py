# This module loads environment-based configuration and runtime paths for the L03_proxy app.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
DEFAULT_REASONING_EFFORT = "low"
DEFAULT_APP_HOST = "127.0.0.1"
DEFAULT_APP_PORT = 3000
DEFAULT_RECENT_MESSAGE_LIMIT = 5
DEFAULT_MAX_TOOL_ITERATIONS = 5
DEFAULT_LLM_TIMEOUT_SECONDS = 30.0
DEFAULT_EXTERNAL_API_TIMEOUT_SECONDS = 10.0
DEFAULT_TOTAL_REQUEST_TIMEOUT_SECONDS = 45.0


@dataclass(frozen=True)
class AppConfig:
    ai_devs_api_key: str
    openai_api_key: str
    openai_model: str
    openai_reasoning_effort: str
    proxy_api_url: str
    app_host: str
    app_port: int
    recent_message_limit: int
    max_tool_iterations_per_request: int
    llm_timeout_seconds: float
    external_api_timeout_seconds: float
    total_request_timeout_seconds: float
    data_dir: Path
    sessions_dir: Path
    logs_dir: Path
    output_dir: Path


def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing.")

    return value


def get_config() -> AppConfig:
    data_dir = Path("data") / "L03_proxy"
    sessions_dir = data_dir / "sessions"
    logs_dir = data_dir / "logs"
    output_dir = data_dir / "output"

    return AppConfig(
        ai_devs_api_key=get_required_env("AI_DEVS_API_KEY"),
        openai_api_key=get_required_env("OPENAI_API_KEY"),
        openai_model=DEFAULT_OPENAI_MODEL,
        openai_reasoning_effort=DEFAULT_REASONING_EFFORT,
        proxy_api_url=get_required_env("L03_PROXY_API_URL"),
        app_host=DEFAULT_APP_HOST,
        app_port=DEFAULT_APP_PORT,
        recent_message_limit=DEFAULT_RECENT_MESSAGE_LIMIT,
        max_tool_iterations_per_request=DEFAULT_MAX_TOOL_ITERATIONS,
        llm_timeout_seconds=DEFAULT_LLM_TIMEOUT_SECONDS,
        external_api_timeout_seconds=DEFAULT_EXTERNAL_API_TIMEOUT_SECONDS,
        total_request_timeout_seconds=DEFAULT_TOTAL_REQUEST_TIMEOUT_SECONDS,
        data_dir=data_dir,
        sessions_dir=sessions_dir,
        logs_dir=logs_dir,
        output_dir=output_dir,
    )


def ensure_runtime_directories(config: AppConfig) -> None:
    # Create the local runtime directories used for sessions, logs, and other app data.
    for path in (
        config.data_dir,
        config.sessions_dir,
        config.logs_dir,
        config.output_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
