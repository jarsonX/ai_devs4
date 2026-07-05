# Configuration loading for the L15_savethem discovery workbench.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

APP_NAME = "L15_savethem"
TASK_NAME = "savethem"
DEFAULT_OPENAI_MODEL = "gpt-5-mini"
DEFAULT_REASONING_EFFORT = "low"
DEFAULT_MAX_ITERATIONS = 20
DEFAULT_MAX_TOOL_CALLS_PER_ITERATION = 1
DEFAULT_REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_MAX_TOOL_RESULT_CHARS = 4_000
DEFAULT_MAX_OUTPUT_TOKENS = 1_200
STARTING_FUEL = 10.0
STARTING_FOOD = 10.0
TLS_CA_BUNDLE = Path("data") / "L6_categorize" / "cache" / "requests_ca_bundle.pem"


# Keep repository-relative paths in one explicit object.
@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    app_dir: Path
    docs_dir: Path
    data_dir: Path
    logs_dir: Path
    output_dir: Path
    cache_dir: Path
    run_report_file: Path
    trace_log_file: Path
    knowledge_file: Path
    route_file: Path


# Store OpenAI settings separately from external API settings.
@dataclass(frozen=True)
class LlmConfig:
    api_key: str
    model_name: str
    reasoning_effort: str
    max_output_tokens: int


# Store course API access and verification settings away from reportable data.
@dataclass(frozen=True)
class ExternalApiConfig:
    api_key: str
    hub_base_url: str
    toolsearch_url: str
    verify_url: str | None
    task_name: str = TASK_NAME


# Store hard limits and local runtime settings.
@dataclass(frozen=True)
class RuntimeConfig:
    max_iterations: int
    max_tool_calls_per_iteration: int
    request_timeout_seconds: int
    max_tool_result_chars: int
    starting_fuel: float
    starting_food: float


# Keep loaded settings in one object passed through the workflow.
@dataclass(frozen=True)
class AppConfig:
    paths: AppPaths
    llm: LlmConfig | None
    external_api: ExternalApiConfig | None
    runtime: RuntimeConfig


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


# Read an integer environment override while keeping a clear fallback.
def get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        return int(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer.") from error


# Build stable repository and runtime paths for the current app.
def build_app_paths() -> AppPaths:
    app_dir = Path(__file__).resolve().parent
    repo_root = Path(__file__).resolve().parents[3]
    docs_dir = app_dir / "docs"
    data_dir = repo_root / "data" / APP_NAME
    logs_dir = data_dir / "logs"
    output_dir = data_dir / "output"
    cache_dir = data_dir / "cache"
    return AppPaths(
        repo_root=repo_root,
        app_dir=app_dir,
        docs_dir=docs_dir,
        data_dir=data_dir,
        logs_dir=logs_dir,
        output_dir=output_dir,
        cache_dir=cache_dir,
        run_report_file=output_dir / "run_report.json",
        trace_log_file=logs_dir / "trace.jsonl",
        knowledge_file=output_dir / "knowledge.json",
        route_file=output_dir / "route.json",
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


# Load OpenAI settings only when a run needs model access.
def load_llm_config(*, required: bool) -> LlmConfig | None:
    if not required and not get_optional_env("OPENAI_API_KEY"):
        return None
    return LlmConfig(
        api_key=get_required_env("OPENAI_API_KEY"),
        model_name=DEFAULT_OPENAI_MODEL,
        reasoning_effort=DEFAULT_REASONING_EFFORT,
        max_output_tokens=get_int_env(
            "L15_MAX_OUTPUT_TOKENS",
            DEFAULT_MAX_OUTPUT_TOKENS,
        ),
    )


# Load course API settings for discovery and optional verification.
def load_external_api_config(*, required: bool) -> ExternalApiConfig | None:
    if (
        not required
        and not get_optional_env("HUB_BASE_URL")
        and not get_optional_env("HUB_TOOLSEARCH_URL")
    ):
        return None

    hub_base_url = get_required_env("HUB_BASE_URL").rstrip("/")

    return ExternalApiConfig(
        api_key=get_required_env("AI_DEVS_API_KEY"),
        hub_base_url=hub_base_url,
        toolsearch_url=get_optional_env("HUB_TOOLSEARCH_URL")
        or f"{hub_base_url}/api/toolsearch",
        verify_url=get_optional_env("HUB_VERIFY_URL"),
    )


# Load local runtime guard settings that keep the agent bounded.
def load_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        max_iterations=get_int_env("L15_MAX_ITERATIONS", DEFAULT_MAX_ITERATIONS),
        max_tool_calls_per_iteration=get_int_env(
            "L15_MAX_TOOL_CALLS_PER_ITERATION",
            DEFAULT_MAX_TOOL_CALLS_PER_ITERATION,
        ),
        request_timeout_seconds=get_int_env(
            "L15_REQUEST_TIMEOUT_SECONDS",
            DEFAULT_REQUEST_TIMEOUT_SECONDS,
        ),
        max_tool_result_chars=get_int_env(
            "L15_MAX_TOOL_RESULT_CHARS",
            DEFAULT_MAX_TOOL_RESULT_CHARS,
        ),
        starting_fuel=STARTING_FUEL,
        starting_food=STARTING_FOOD,
    )


# Load all config while allowing local import checks to skip secrets.
def load_app_config(
    *,
    require_llm: bool = True,
    require_external_api: bool = True,
) -> AppConfig:
    return AppConfig(
        paths=build_app_paths(),
        llm=load_llm_config(required=require_llm),
        external_api=load_external_api_config(required=require_external_api),
        runtime=load_runtime_config(),
    )


# Create runtime directories before the workflow writes logs or reports.
def ensure_runtime_directories(paths: AppPaths) -> None:
    for path in (
        paths.data_dir,
        paths.logs_dir,
        paths.output_dir,
        paths.cache_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)


# Return a secret-safe summary that local checks can print.
def build_safe_config_summary(config: AppConfig) -> dict[str, object]:
    return {
        "app": APP_NAME,
        "data_dir": str(config.paths.data_dir.relative_to(config.paths.repo_root)),
        "llm": {
            "loaded": config.llm is not None,
            "api_key": "configured" if config.llm else "not_loaded",
            "model_name": config.llm.model_name if config.llm else None,
            "reasoning_effort": config.llm.reasoning_effort if config.llm else None,
            "max_output_tokens": config.llm.max_output_tokens if config.llm else None,
        },
        "external_api": {
            "loaded": config.external_api is not None,
            "api_key": "configured" if config.external_api else "not_loaded",
            "hub_base_url": "configured" if config.external_api else "not_loaded",
            "toolsearch_url": "configured" if config.external_api else "not_loaded",
            "verify_url": "configured" if config.external_api and config.external_api.verify_url else "not_loaded",
        },
        "runtime": {
            "max_iterations": config.runtime.max_iterations,
            "max_tool_calls_per_iteration": config.runtime.max_tool_calls_per_iteration,
            "request_timeout_seconds": config.runtime.request_timeout_seconds,
            "max_tool_result_chars": config.runtime.max_tool_result_chars,
            "starting_fuel": config.runtime.starting_fuel,
            "starting_food": config.runtime.starting_food,
        },
    }
