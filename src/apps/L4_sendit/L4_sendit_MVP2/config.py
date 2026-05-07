# Path and model configuration for the L4 sendit MVP2 Stage 1-6 workflow.

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
# Store repository-relative runtime paths used by the MVP2 Stage 1-6 pipeline.
class AppPaths:
    repo_root: Path
    command_file: Path
    references_dir: Path
    output_dir: Path
    task_understanding_output_file: Path
    raw_task_understanding_output_file: Path
    reference_inventory_output_file: Path
    selected_sources_output_file: Path
    raw_source_selection_output_file: Path
    evidence_context_output_file: Path
    evidence_package_output_file: Path
    raw_evidence_extraction_output_file: Path
    task_result_output_file: Path
    raw_task_execution_output_file: Path
    final_output_text_file: Path
    final_output_json_file: Path
    declaration_output_file: Path
    run_report_output_file: Path


@dataclass(frozen=True)
# Store OpenAI-backed Stage 1-6 settings loaded only for real model calls.
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
    selected_command_file = (command_file or data_dir / "input" / "command.txt").resolve()

    return AppPaths(
        repo_root=repo_root,
        command_file=selected_command_file,
        references_dir=data_dir / "references",
        output_dir=output_dir,
        task_understanding_output_file=output_dir / "task_understanding.json",
        raw_task_understanding_output_file=output_dir / "model_task_understanding_raw.json",
        reference_inventory_output_file=output_dir / "reference_inventory.json",
        selected_sources_output_file=output_dir / "selected_sources.json",
        raw_source_selection_output_file=output_dir / "model_source_selection_raw.json",
        evidence_context_output_file=output_dir / "evidence_context.json",
        evidence_package_output_file=output_dir / "evidence_package.json",
        raw_evidence_extraction_output_file=output_dir / "model_evidence_extraction_raw.json",
        task_result_output_file=output_dir / "task_result.json",
        raw_task_execution_output_file=output_dir / "model_task_execution_raw.json",
        final_output_text_file=output_dir / "final_output.txt",
        final_output_json_file=output_dir / "final_output.json",
        declaration_output_file=output_dir / "declaration.txt",
        run_report_output_file=output_dir / "run_report.md",
    )


# Load OpenAI settings only when the user chooses a real model call.
def load_model_config() -> ModelConfig:
    return ModelConfig(
        api_key=_get_required_env("OPENAI_API_KEY"),
        command_parse_model=os.getenv("OPENAI_MODEL", DEFAULT_COMMAND_PARSE_MODEL).strip(),
        source_selection_model=os.getenv(
            "OPENAI_SOURCE_SELECTION_MODEL",
            DEFAULT_SOURCE_SELECTION_MODEL,
        ).strip(),
        text_extraction_model=os.getenv(
            "OPENAI_TEXT_EXTRACTION_MODEL",
            DEFAULT_TEXT_EXTRACTION_MODEL,
        ).strip(),
        vision_extraction_model=os.getenv(
            "OPENAI_VISION_EXTRACTION_MODEL",
            DEFAULT_VISION_EXTRACTION_MODEL,
        ).strip(),
        reasoning_model=os.getenv(
            "OPENAI_REASONING_MODEL",
            DEFAULT_REASONING_MODEL,
        ).strip(),
        max_model_requests=DEFAULT_MAX_MODEL_REQUESTS,
    )


# Read one required environment variable and fail with a clear learning error.
def _get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing.")

    return value
