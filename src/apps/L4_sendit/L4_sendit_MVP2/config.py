# Path, model, and guard configuration for the L4 sendit MVP2 learning app.

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

DEFAULT_COMMAND_PARSE_MODEL = "gpt-5.4-mini"
DEFAULT_SOURCE_SELECTION_MODEL = "gpt-5.4-mini"
DEFAULT_TEXT_EXTRACTION_MODEL = "gpt-5.4-mini"
DEFAULT_VISION_EXTRACTION_MODEL = "gpt-5.4-mini"
DEFAULT_REASONING_MODEL = "gpt-5.5"
DEFAULT_MAX_MODEL_REQUESTS = 1


@dataclass(frozen=True)
# Store repository-relative runtime paths used by the MVP2 pipeline.
class AppPaths:
    repo_root: Path
    command_file: Path
    references_dir: Path
    output_dir: Path
    parsed_command_output_file: Path
    raw_command_parse_output_file: Path
    extracted_facts_output_file: Path
    declaration_data_output_file: Path
    declaration_output_file: Path
    verification_payload_output_file: Path
    hub_response_output_file: Path
    run_report_output_file: Path


@dataclass(frozen=True)
# Store OpenAI model settings and the explicit model-call guard.
class ModelConfig:
    api_key: str
    command_parse_model: str
    source_selection_model: str
    text_extraction_model: str
    vision_extraction_model: str
    reasoning_model: str
    max_model_requests: int


# Build default paths while allowing the command file to be overridden.
def build_app_paths(command_file: Path | None = None) -> AppPaths:
    repo_root = Path(__file__).resolve().parents[4]
    data_dir = repo_root / "data" / "L4_sendit"
    output_dir = data_dir / "output"
    selected_command_file = command_file or data_dir / "input" / "command.txt"

    return AppPaths(
        repo_root=repo_root,
        command_file=selected_command_file,
        references_dir=data_dir / "references",
        output_dir=output_dir,
        parsed_command_output_file=output_dir / "parsed_command.json",
        raw_command_parse_output_file=output_dir / "model_command_parse_raw.json",
        extracted_facts_output_file=output_dir / "extracted_facts.json",
        declaration_data_output_file=output_dir / "declaration_data.json",
        declaration_output_file=output_dir / "declaration.txt",
        verification_payload_output_file=output_dir / "verification_payload.json",
        hub_response_output_file=output_dir / "hub_response.json",
        run_report_output_file=output_dir / "run_report.md",
    )


# Load AI command parser settings only when a real model call is needed.
def load_model_config() -> ModelConfig:
    return ModelConfig(
        api_key=_get_required_env("OPENAI_API_KEY"),
        command_parse_model=DEFAULT_COMMAND_PARSE_MODEL,
        source_selection_model=DEFAULT_SOURCE_SELECTION_MODEL,
        text_extraction_model=DEFAULT_TEXT_EXTRACTION_MODEL,
        vision_extraction_model=DEFAULT_VISION_EXTRACTION_MODEL,
        reasoning_model=DEFAULT_REASONING_MODEL,
        max_model_requests=DEFAULT_MAX_MODEL_REQUESTS,
    )


# Read one required string environment variable and fail clearly.
def _get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing.")

    return value
