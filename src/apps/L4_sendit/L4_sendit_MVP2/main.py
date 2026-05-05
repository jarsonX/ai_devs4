# Command-line entrypoint for the L4 sendit MVP2 Stage 1 pipeline.

import argparse
from pathlib import Path

from src.apps.L4_sendit.L4_sendit_MVP1.config import HubConfig, load_hub_config
from src.apps.L4_sendit.L4_sendit_MVP1.declaration_builder import (
    build_declaration_data,
    render_declaration,
)
from src.apps.L4_sendit.L4_sendit_MVP1.fact_extractor import (
    calculate_wagon_details,
    load_static_facts,
)
from src.apps.L4_sendit.L4_sendit_MVP1.hub_client import (
    build_verification_payload,
    mask_payload_for_storage,
    submit_verification,
)
from src.apps.L4_sendit.L4_sendit_MVP1.output import (
    save_declaration,
    save_json,
    save_run_report,
)
from src.apps.L4_sendit.L4_sendit_MVP1.reference_loader import load_declaration_template
from src.apps.L4_sendit.L4_sendit_MVP1.validator import validate_run
from src.apps.L4_sendit.L4_sendit_MVP2.command_parser import (
    load_mock_model_response,
    parse_command_from_mock,
    parse_command_with_ai,
)
from src.apps.L4_sendit.L4_sendit_MVP2.config import build_app_paths, load_model_config
from src.apps.L4_sendit.L4_sendit_MVP2.report_builder import build_run_report
from src.apps.L4_sendit.L4_sendit_MVP2.validator import validate_parsed_command


# Run MVP2 Stage 1: AI parse command, then reuse deterministic MVP1 pipeline.
def main() -> None:
    args = _parse_args()
    paths = build_app_paths(command_file=args.command_file)

    command_text = paths.command_file.read_text(encoding="utf-8")
    parse_result, model_source = _parse_command(args, command_text)
    command_validation_results = validate_parsed_command(parse_result.parsed_command)

    facts = load_static_facts()
    template_text = load_declaration_template(paths.references_dir)
    declaration_data = build_declaration_data(parse_result.shipment_command, facts)
    declaration_text = render_declaration(declaration_data, template_text)
    wagon_calculation = calculate_wagon_details(parse_result.shipment_command, facts)
    validation_results = validate_run(
        command=parse_result.shipment_command,
        facts=facts,
        declaration_data=declaration_data,
        wagon_calculation=wagon_calculation,
        declaration_text=declaration_text,
        template_text=template_text,
    )
    report_text = build_run_report(
        parsed_command=parse_result.parsed_command,
        command_validation_results=command_validation_results,
        facts=facts,
        declaration_data=declaration_data,
        wagon_calculation=wagon_calculation,
        validation_results=validation_results,
        loaded_references=[
            "data/L4_sendit/input/command.txt",
            "data/L4_sendit/references/zalacznik-E.md",
            "data/L4_sendit/references/index.md",
            "data/L4_sendit/references/trasy-wylaczone.png",
            "data/L4_sendit/references/dodatkowe-wagony.md",
            "data/L4_sendit/references/zalacznik-G.md",
        ],
        model_source=model_source,
    )

    hub_response = None
    if args.submit:
        _raise_if_validation_has_errors(validation_results)
        hub_config = load_hub_config()
        verification_payload = build_verification_payload(hub_config, declaration_text)
        hub_response = submit_verification(hub_config, verification_payload)
    else:
        hub_config = _build_masked_payload_config()
        verification_payload = build_verification_payload(hub_config, declaration_text)

    save_json(paths.parsed_command_output_file, parse_result.parsed_command.model_dump(mode="json"))
    save_json(paths.raw_command_parse_output_file, parse_result.raw_model_response)
    save_json(paths.extracted_facts_output_file, facts)
    save_json(paths.declaration_data_output_file, declaration_data)
    save_json(paths.verification_payload_output_file, mask_payload_for_storage(verification_payload))
    save_declaration(paths.declaration_output_file, declaration_text)
    save_run_report(paths.run_report_output_file, report_text)
    if hub_response is not None:
        save_json(paths.hub_response_output_file, hub_response)


# Parse command-line arguments for the MVP2 Stage 1 runner.
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the L4 sendit MVP2 Stage 1 declaration.")
    parser.add_argument(
        "--command-file",
        type=Path,
        default=None,
        help="Optional path to the operational command file.",
    )
    parser.add_argument(
        "--mock-model-output-file",
        type=Path,
        default=None,
        help="Optional JSON file that replaces the real AI command parser call.",
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Submit the generated declaration to the course Hub.",
    )

    return parser.parse_args()


# Choose between a real guarded model call and local mock validation.
def _parse_command(args: argparse.Namespace, command_text: str):
    if args.mock_model_output_file is not None:
        raw_json_text = args.mock_model_output_file.read_text(encoding="utf-8")
        raw_model_response = load_mock_model_response(raw_json_text)
        return parse_command_from_mock(command_text, raw_model_response), "mock-model-output-file"

    model_config = load_model_config()
    return parse_command_with_ai(command_text, model_config), model_config.command_parse_model


# Fail before Hub submission if any deterministic validation check is an error.
def _raise_if_validation_has_errors(validation_results: list) -> None:
    error_messages = [
        validation_result.message
        for validation_result in validation_results
        if validation_result.status == "ERROR"
    ]
    if error_messages:
        raise ValueError(f"Cannot submit with validation errors: {', '.join(error_messages)}")


# Build non-secret config used only to create a masked payload review artifact.
def _build_masked_payload_config() -> HubConfig:
    return HubConfig(
        api_key="not-loaded-without-submit",
        verify_url="not-loaded-without-submit",
        task_name="sendit",
    )


if __name__ == "__main__":
    main()
