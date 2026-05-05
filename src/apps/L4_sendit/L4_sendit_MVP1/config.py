# Path and environment configuration for the L4 sendit MVP1 learning app.

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
# Store repository-relative runtime paths used by the MVP1 pipeline.
class AppPaths:
    repo_root: Path
    command_file: Path
    references_dir: Path
    output_dir: Path
    parsed_command_output_file: Path
    extracted_facts_output_file: Path
    declaration_data_output_file: Path
    declaration_output_file: Path
    verification_payload_output_file: Path
    hub_response_output_file: Path
    run_report_output_file: Path


@dataclass(frozen=True)
# Store secret-bearing Hub configuration loaded only for explicit submission.
class HubConfig:
    api_key: str
    verify_url: str
    task_name: str


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
        extracted_facts_output_file=output_dir / "extracted_facts.json",
        declaration_data_output_file=output_dir / "declaration_data.json",
        declaration_output_file=output_dir / "declaration.txt",
        verification_payload_output_file=output_dir / "verification_payload.json",
        hub_response_output_file=output_dir / "hub_response.json",
        run_report_output_file=output_dir / "run_report.md",
    )


# Load Hub configuration only when the user explicitly requests submission.
def load_hub_config() -> HubConfig:
    return HubConfig(
        api_key=_get_required_env("AI_DEVS_API_KEY"),
        verify_url=_get_required_env("HUB_VERIFY_URL"),
        task_name="sendit",
    )


# Read one required environment variable and fail with a clear learning error.
def _get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing.")

    return value
