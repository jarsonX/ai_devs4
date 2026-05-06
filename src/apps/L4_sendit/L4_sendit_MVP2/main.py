# Command-line entrypoint for the L4 sendit MVP2 Stage 1-5 workflow.

import argparse
from pathlib import Path

from src.apps.L4_sendit.L4_sendit_MVP2.config import (
    build_app_paths,
    load_model_config,
)
from src.apps.L4_sendit.L4_sendit_MVP2.fact_extractor import (
    extract_evidence_from_mock,
    extract_evidence_with_ai,
    load_mock_evidence_response,
)
from src.apps.L4_sendit.L4_sendit_MVP2.output import save_json, save_run_report
from src.apps.L4_sendit.L4_sendit_MVP2.reference_inventory import build_reference_inventory
from src.apps.L4_sendit.L4_sendit_MVP2.report_builder import build_run_report
from src.apps.L4_sendit.L4_sendit_MVP2.source_selector import (
    load_mock_source_selection_response,
    select_sources_from_mock,
    select_sources_with_ai,
)
from src.apps.L4_sendit.L4_sendit_MVP2.task_executor import execute_task
from src.apps.L4_sendit.L4_sendit_MVP2.task_registry import build_supported_task_map
from src.apps.L4_sendit.L4_sendit_MVP2.task_understanding import (
    load_mock_task_understanding_response,
    understand_task_from_mock,
    understand_task_with_ai,
)
from src.apps.L4_sendit.L4_sendit_MVP2.validator import (
    validate_evidence_package,
    validate_task_result,
    raise_if_reference_inventory_invalid,
    validate_reference_inventory,
    validate_selected_sources,
    validate_task_understanding,
)


# Run MVP2 Stage 1-5: understand the task, build inventory, select sources, extract evidence, execute the task, and save artifacts.
def main() -> None:
    args = _parse_args()
    paths = build_app_paths(command_file=args.command_file)
    supported_tasks = build_supported_task_map()

    command_text = paths.command_file.read_text(encoding="utf-8")
    task_understanding_result, task_understanding_model_source = _understand_task(args, command_text, supported_tasks)
    task_understanding_validation_results = validate_task_understanding(
        task_understanding_result.task_understanding,
        supported_tasks,
    )
    reference_inventory = build_reference_inventory(paths.repo_root, paths.references_dir)
    reference_inventory_validation_results = validate_reference_inventory(
        reference_inventory,
        str(paths.repo_root),
    )
    raise_if_reference_inventory_invalid(reference_inventory_validation_results)
    source_selection_result, source_selection_model_source = _select_sources(
        args=args,
        task_understanding=task_understanding_result.task_understanding,
        reference_inventory=reference_inventory,
        supported_tasks=supported_tasks,
    )
    selected_sources_validation_results = validate_selected_sources(
        selected_sources=source_selection_result.selected_sources,
        task_understanding=task_understanding_result.task_understanding,
        reference_inventory=reference_inventory,
        supported_tasks=supported_tasks,
    )
    evidence_extraction_result, evidence_extraction_model_source = _extract_evidence(
        args=args,
        task_understanding=task_understanding_result.task_understanding,
        selected_sources=source_selection_result.selected_sources,
        repo_root=paths.repo_root,
        supported_tasks=supported_tasks,
    )
    evidence_validation_results = validate_evidence_package(
        evidence_package=evidence_extraction_result.evidence_package,
        evidence_context=evidence_extraction_result.evidence_context,
        task_understanding=task_understanding_result.task_understanding,
        selected_sources=source_selection_result.selected_sources,
        markdown_source_texts=_load_markdown_source_texts(
            repo_root=paths.repo_root,
            selected_sources=source_selection_result.selected_sources,
        ),
        supported_tasks=supported_tasks,
    )
    task_execution_result = execute_task(
        task_understanding=task_understanding_result.task_understanding,
        evidence_package=evidence_extraction_result.evidence_package,
        supported_tasks=supported_tasks,
    )
    task_result_validation_results = validate_task_result(
        task_result=task_execution_result.task_result,
        task_understanding=task_understanding_result.task_understanding,
        evidence_package=evidence_extraction_result.evidence_package,
        executor_definition=_get_executor_definition(task_understanding_result.task_understanding.task_name),
        supported_tasks=supported_tasks,
    )
    report_text = build_run_report(
        command_file=str(paths.command_file.relative_to(paths.repo_root)),
        task_understanding=task_understanding_result.task_understanding,
        task_understanding_validation_results=task_understanding_validation_results,
        reference_inventory=reference_inventory,
        reference_inventory_validation_results=reference_inventory_validation_results,
        selected_sources=source_selection_result.selected_sources,
        selected_sources_validation_results=selected_sources_validation_results,
        evidence_package=evidence_extraction_result.evidence_package,
        evidence_validation_results=evidence_validation_results,
        task_result=task_execution_result.task_result,
        task_result_validation_results=task_result_validation_results,
        model_source=task_understanding_model_source,
        source_selection_model_source=source_selection_model_source,
        evidence_extraction_model_source=evidence_extraction_model_source,
        task_execution_source="deterministic-registered-executor",
    )

    save_json(paths.task_understanding_output_file, task_understanding_result.task_understanding)
    save_json(paths.raw_task_understanding_output_file, task_understanding_result.raw_model_response)
    save_json(paths.reference_inventory_output_file, reference_inventory)
    save_json(paths.selected_sources_output_file, source_selection_result.selected_sources)
    save_json(paths.raw_source_selection_output_file, source_selection_result.raw_model_response)
    save_json(paths.evidence_context_output_file, evidence_extraction_result.evidence_context)
    save_json(paths.evidence_package_output_file, evidence_extraction_result.evidence_package)
    save_json(paths.raw_evidence_extraction_output_file, evidence_extraction_result.raw_model_response)
    save_json(paths.task_result_output_file, task_execution_result.task_result)
    save_json(paths.raw_task_execution_output_file, task_execution_result.raw_model_response)
    save_run_report(paths.run_report_output_file, report_text)


# Parse command-line arguments for the MVP2 Stage 1-5 runner.
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the L4 sendit MVP2 Stage 1-5 workflow.")
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
        help="Optional JSON file that replaces the real Stage 1 model call.",
    )
    parser.add_argument(
        "--mock-source-selection-output-file",
        type=Path,
        default=None,
        help="Optional JSON file that replaces the real Stage 3 model call.",
    )
    parser.add_argument(
        "--mock-evidence-output-file",
        type=Path,
        default=None,
        help="Optional JSON file that replaces the real Stage 4 model call.",
    )

    return parser.parse_args()


# Run a real or mock Stage 1 command understanding step.
def _understand_task(
    args: argparse.Namespace,
    command_text: str,
    supported_tasks: dict,
):
    if args.mock_model_output_file is not None:
        raw_json_text = args.mock_model_output_file.read_text(encoding="utf-8")
        raw_model_response = load_mock_task_understanding_response(raw_json_text)
        return understand_task_from_mock(raw_model_response, supported_tasks), "mock-model-output-file"

    model_config = load_model_config()
    return (
        understand_task_with_ai(command_text, model_config, supported_tasks),
        model_config.command_parse_model,
    )


# Run a real or mock Stage 3 source selection step.
def _select_sources(
    args: argparse.Namespace,
    task_understanding,
    reference_inventory,
    supported_tasks: dict,
):
    if args.mock_source_selection_output_file is not None:
        raw_json_text = args.mock_source_selection_output_file.read_text(encoding="utf-8")
        raw_model_response = load_mock_source_selection_response(raw_json_text)
        return (
            select_sources_from_mock(
                raw_model_response=raw_model_response,
                task_understanding=task_understanding,
                reference_inventory=reference_inventory,
                supported_tasks=supported_tasks,
            ),
            "mock-source-selection-output-file",
        )

    model_config = load_model_config()
    return (
        select_sources_with_ai(
            task_understanding=task_understanding,
            reference_inventory=reference_inventory,
            model_config=model_config,
            supported_tasks=supported_tasks,
        ),
        model_config.source_selection_model,
    )


# Run a real or mock Stage 4 evidence extraction step.
def _extract_evidence(
    args: argparse.Namespace,
    task_understanding,
    selected_sources,
    repo_root: Path,
    supported_tasks: dict,
):
    if args.mock_evidence_output_file is not None:
        raw_json_text = args.mock_evidence_output_file.read_text(encoding="utf-8")
        raw_model_response = load_mock_evidence_response(raw_json_text)
        return (
            extract_evidence_from_mock(
                raw_model_response=raw_model_response,
                task_understanding=task_understanding,
                selected_sources=selected_sources,
                repo_root=repo_root,
                supported_tasks=supported_tasks,
            ),
            "mock-evidence-output-file",
        )

    model_config = load_model_config()
    return extract_evidence_with_ai(
        task_understanding=task_understanding,
        selected_sources=selected_sources,
        repo_root=repo_root,
        model_config=model_config,
        supported_tasks=supported_tasks,
    )


# Load markdown source text again for deterministic evidence validation in main.
def _load_markdown_source_texts(repo_root: Path, selected_sources) -> dict[str, str]:
    markdown_source_texts: dict[str, str] = {}
    for source in selected_sources.selected_sources:
        if source.source_type != "markdown":
            continue
        source_path = (repo_root / source.path).resolve()
        markdown_source_texts[source.path] = source_path.read_text(encoding="utf-8")

    return markdown_source_texts


# Get the registered executor definition needed for Stage 5 validation in main.
def _get_executor_definition(task_name: str):
    from src.apps.L4_sendit.L4_sendit_MVP2.task_executor import EXECUTOR_REGISTRY

    executor_definition = EXECUTOR_REGISTRY.get(task_name)
    if executor_definition is None:
        raise ValueError(f"No executor definition found for task_name: {task_name}")

    return executor_definition


if __name__ == "__main__":
    main()
