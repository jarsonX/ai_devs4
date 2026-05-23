# Configuration loading for the L7 electricity learning app.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv


load_dotenv()

TASK_NAME = "electricity"
DEFAULT_MAX_ROTATIONS = 24
DEFAULT_VISION_MODEL = "gpt-5.5"


# Store repository-relative paths used by the L7 electricity workflow.
@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    app_dir: Path
    docs_dir: Path
    data_dir: Path
    input_dir: Path
    references_dir: Path
    output_dir: Path
    cache_dir: Path
    tile_cache_dir: Path
    current_board_file: Path
    solved_board_file: Path
    request_log_file: Path
    response_log_file: Path
    run_report_file: Path
    rotation_plan_file: Path
    parser_failure_file: Path


# Store secret-bearing Hub configuration required by the app.
@dataclass(frozen=True)
class HubConfig:
    api_key: str
    data_base_url: str
    verify_url: str
    solved_image_url: str
    task_name: str = TASK_NAME


# Store runtime flags that shape later workflow behavior.
@dataclass(frozen=True)
class RuntimeConfig:
    reset_on_start: bool
    max_rotations: int


# Store secret-bearing OpenAI vision configuration for tile parsing.
@dataclass(frozen=True)
class VisionConfig:
    openai_api_key: str
    model_name: str


# Store all configuration required by the current application skeleton.
@dataclass(frozen=True)
class AppConfig:
    paths: AppPaths
    hub: HubConfig
    runtime: RuntimeConfig
    vision: VisionConfig


# Build stable repository-relative data paths for the L7 app package.
def build_app_paths() -> AppPaths:
    app_dir = Path(__file__).resolve().parent
    repo_root = Path(__file__).resolve().parents[3]
    docs_dir = app_dir / "docs"
    data_dir = repo_root / "data" / "L7_electricity"
    input_dir = data_dir / "input"
    references_dir = data_dir / "references"
    output_dir = data_dir / "output"
    cache_dir = data_dir / "cache"
    tile_cache_dir = cache_dir / "tiles"

    return AppPaths(
        repo_root=repo_root,
        app_dir=app_dir,
        docs_dir=docs_dir,
        data_dir=data_dir,
        input_dir=input_dir,
        references_dir=references_dir,
        output_dir=output_dir,
        cache_dir=cache_dir,
        tile_cache_dir=tile_cache_dir,
        current_board_file=input_dir / "current_board.png",
        solved_board_file=references_dir / "solved_board.png",
        request_log_file=output_dir / "request_log.jsonl",
        response_log_file=output_dir / "response_log.jsonl",
        run_report_file=output_dir / "run_report.json",
        rotation_plan_file=output_dir / "rotation_plan.json",
        parser_failure_file=output_dir / "parser_failure.json",
    )


# Read one required environment variable and fail with a clear setup error.
def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing.")

    return value


# Read one optional environment variable and normalize empty values to None.
def get_optional_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


# Parse one optional boolean environment variable using explicit truthy values.
def get_optional_bool_env(name: str, default: bool) -> bool:
    value = get_optional_env(name)
    if value is None:
        return default

    normalized_value = value.lower()
    if normalized_value in {"1", "true", "yes", "on"}:
        return True
    if normalized_value in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"{name} must be a boolean-like value.")


# Parse one optional positive integer environment variable with a lower bound.
def get_optional_int_env(name: str, default: int, minimum: int = 1) -> int:
    value = get_optional_env(name)
    if value is None:
        return default

    try:
        parsed_value = int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer.") from error

    if parsed_value < minimum:
        raise ValueError(f"{name} must be >= {minimum}.")

    return parsed_value


# Load the Hub configuration required by the L7 electricity workflow.
def load_hub_config() -> HubConfig:
    verify_url = get_required_env("HUB_VERIFY_URL")
    return HubConfig(
        api_key=get_required_env("AI_DEVS_API_KEY"),
        data_base_url=resolve_hub_data_base_url(verify_url),
        verify_url=verify_url,
        solved_image_url=resolve_solved_image_url(verify_url),
    )


# Load runtime flags used by later workflow steps.
def load_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        reset_on_start=get_optional_bool_env("L7_ELECTRICITY_RESET_ON_START", default=False),
        max_rotations=get_optional_int_env(
            "L7_ELECTRICITY_MAX_ROTATIONS",
            default=DEFAULT_MAX_ROTATIONS,
        ),
    )


# Load the OpenAI vision configuration required by the image parser.
def load_vision_config() -> VisionConfig:
    return VisionConfig(
        openai_api_key=get_required_env("OPENAI_API_KEY"),
        model_name=get_optional_env("L7_ELECTRICITY_VISION_MODEL") or DEFAULT_VISION_MODEL,
    )


# Load all app configuration from package metadata and environment variables.
def load_app_config() -> AppConfig:
    return AppConfig(
        paths=build_app_paths(),
        hub=load_hub_config(),
        runtime=load_runtime_config(),
        vision=load_vision_config(),
    )


# Create local runtime directories needed by later workflow steps.
def ensure_runtime_directories(paths: AppPaths) -> None:
    for path in (
        paths.data_dir,
        paths.input_dir,
        paths.references_dir,
        paths.output_dir,
        paths.cache_dir,
        paths.tile_cache_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)


# Resolve the board data base URL from explicit config or the shared verify URL.
def resolve_hub_data_base_url(verify_url: str) -> str:
    explicit_value = get_optional_env("HUB_DATA_BASE_URL")
    if explicit_value is not None:
        return explicit_value

    verify_parts = urlsplit(verify_url)
    return urlunsplit((verify_parts.scheme, verify_parts.netloc, "/data", "", ""))


# Resolve the solved reference image URL from explicit config or the shared verify URL.
def resolve_solved_image_url(verify_url: str) -> str:
    explicit_value = get_optional_env("HUB_SOLVED_IMAGE_URL")
    if explicit_value is not None:
        return explicit_value

    verify_parts = urlsplit(verify_url)
    return urlunsplit((verify_parts.scheme, verify_parts.netloc, "/i/solved_electricity.png", "", ""))
