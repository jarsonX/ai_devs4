# Guarded end-to-end workflow for the L7 electricity puzzle.

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.apps.L7_electricity.L7_electricity_gpt_5_5.config import AppConfig, ensure_runtime_directories
from src.apps.L7_electricity.L7_electricity_gpt_5_5.hub_client import HubClient, HubImageResponse, HubVerifyResponse
from src.apps.L7_electricity.L7_electricity_gpt_5_5.image_parser import BoardParseResult, ImageParser, ParsedTileResult
from src.apps.L7_electricity.L7_electricity_gpt_5_5.logging_utils import (
    append_request_log,
    append_response_log,
    build_current_board_request_record,
    build_image_response_record,
    build_rotate_request_record,
    build_solved_board_request_record,
    build_verify_response_record,
    write_json_file,
)
from src.apps.L7_electricity.L7_electricity_gpt_5_5.solver import BoardRotationPlan, solve_board


FLAG_PATTERN = re.compile(r"\{FLG:[^}]+}")


# Store one guarded electricity run outcome together with key workflow artifacts.
@dataclass(frozen=True)
class ElectricityRunResult:
    run_id: str
    started_at: str
    ended_at: str
    success: bool
    reset_used: bool
    max_rotations: int
    planned_rotations: int
    executed_rotations: int
    guard_triggered: bool
    completion_flag: str | None
    current_board_map: dict[str, list[str]]
    solved_board_map: dict[str, list[str]]
    final_board_map: dict[str, list[str]]
    rotation_sequence_planned: list[str]
    rotation_sequence_executed: list[str]
    parser_used_cache_for_solved: bool
    parser_used_cache_for_current: bool
    parser_used_cache_for_final: bool
    diagnostic_run_dir: str
    error_summary: str | None = None


# Run the full electricity workflow while respecting a hard rotation-request cap.
def run_guarded_workflow(
    config: AppConfig,
    *,
    client: HubClient | None = None,
    parser: ImageParser | None = None,
    max_rotations_override: int | None = None,
    reset_override: bool | None = None,
) -> ElectricityRunResult:
    ensure_runtime_directories(config.paths)
    selected_client = client or HubClient(config.hub)
    selected_parser = parser or ImageParser(config)
    max_rotations = max_rotations_override or config.runtime.max_rotations
    reset_used = config.runtime.reset_on_start if reset_override is None else reset_override
    run_id = build_run_id()
    started_at = current_timestamp()

    current_board_response = selected_client.download_current_board(reset=reset_used)
    config.paths.current_board_file.write_bytes(current_board_response.content)
    append_request_log(
        config.paths,
        with_run_id(build_current_board_request_record(reset_used), run_id),
    )
    append_response_log(
        config.paths,
        with_run_id(
            build_image_response_record(current_board_response, kind="download_current_board"),
            run_id,
        ),
    )

    solved_board_response = selected_client.download_solved_board()
    config.paths.solved_board_file.write_bytes(solved_board_response.content)
    append_request_log(
        config.paths,
        with_run_id(build_solved_board_request_record(), run_id),
    )
    append_response_log(
        config.paths,
        with_run_id(
            build_image_response_record(solved_board_response, kind="download_solved_board"),
            run_id,
        ),
    )

    current_parse_result = selected_parser.parse_current_board()
    save_parse_snapshot(
        config=config,
        run_id=run_id,
        phase_name="current_before_rotations",
        parse_result=current_parse_result,
        source_image_response=current_board_response,
    )
    solved_parse_result = selected_parser.parse_solved_board()
    save_parse_snapshot(
        config=config,
        run_id=run_id,
        phase_name="solved_reference",
        parse_result=solved_parse_result,
        source_image_response=solved_board_response,
    )
    rotation_plan = solve_board(current_parse_result.board, solved_parse_result.board)
    executed_sequence = rotation_plan.rotation_sequence[:max_rotations]
    guard_triggered = rotation_plan.total_rotations > max_rotations
    completion_flag: str | None = None

    save_rotation_plan(
        config=config,
        run_id=run_id,
        started_at=started_at,
        max_rotations=max_rotations,
        current_parse_result=current_parse_result,
        solved_parse_result=solved_parse_result,
        rotation_plan=rotation_plan,
        executed_sequence=executed_sequence,
        guard_triggered=guard_triggered,
    )

    for coordinate_label in executed_sequence:
        append_request_log(
            config.paths,
            with_run_id(build_rotate_request_record(config.hub, coordinate_label), run_id),
        )
        verify_response = selected_client.rotate_tile_once(coordinate_label)
        append_response_log(
            config.paths,
            with_run_id(
                build_verify_response_record(
                    verify_response,
                    kind="rotate_tile_once",
                    coordinate_label=coordinate_label,
                ),
                run_id,
            ),
        )

        completion_flag = extract_flag(verify_response)
        if completion_flag is not None:
            break

    final_board_response = selected_client.download_current_board(reset=False)
    config.paths.current_board_file.write_bytes(final_board_response.content)
    append_request_log(
        config.paths,
        with_run_id(build_current_board_request_record(False), run_id),
    )
    append_response_log(
        config.paths,
        with_run_id(
            build_image_response_record(final_board_response, kind="download_current_board_after_batch"),
            run_id,
        ),
    )
    final_parse_result = selected_parser.parse_current_board()
    save_parse_snapshot(
        config=config,
        run_id=run_id,
        phase_name="current_after_batch",
        parse_result=final_parse_result,
        source_image_response=final_board_response,
    )

    ended_at = current_timestamp()
    diagnostic_run_dir = str(get_diagnostic_run_dir(config, run_id))
    result = ElectricityRunResult(
        run_id=run_id,
        started_at=started_at,
        ended_at=ended_at,
        success=completion_flag is not None,
        reset_used=reset_used,
        max_rotations=max_rotations,
        planned_rotations=rotation_plan.total_rotations,
        executed_rotations=len(executed_sequence),
        guard_triggered=guard_triggered,
        completion_flag=completion_flag,
        current_board_map=current_parse_result.board.to_label_map(),
        solved_board_map=solved_parse_result.board.to_label_map(),
        final_board_map=final_parse_result.board.to_label_map(),
        rotation_sequence_planned=rotation_plan.rotation_sequence,
        rotation_sequence_executed=executed_sequence,
        parser_used_cache_for_solved=solved_parse_result.used_cache,
        parser_used_cache_for_current=current_parse_result.used_cache,
        parser_used_cache_for_final=final_parse_result.used_cache,
        diagnostic_run_dir=diagnostic_run_dir,
        error_summary=build_error_summary(rotation_plan, executed_sequence, completion_flag),
    )
    save_run_report(config, result)
    return result


# Save one JSON rotation plan artifact for review and debugging.
def save_rotation_plan(
    *,
    config: AppConfig,
    run_id: str,
    started_at: str,
    max_rotations: int,
    current_parse_result: BoardParseResult,
    solved_parse_result: BoardParseResult,
    rotation_plan: BoardRotationPlan,
    executed_sequence: list[str],
    guard_triggered: bool,
) -> None:
    write_json_file(
        config.paths.rotation_plan_file,
        {
            "run_id": run_id,
            "generated_at": started_at,
            "max_rotations": max_rotations,
            "planned_rotations": rotation_plan.total_rotations,
            "guard_triggered": guard_triggered,
            "current_board_map": current_parse_result.board.to_label_map(),
            "solved_board_map": solved_parse_result.board.to_label_map(),
            "rotation_map": rotation_plan.to_rotation_map(),
            "rotation_sequence_planned": rotation_plan.rotation_sequence,
            "rotation_sequence_executed": executed_sequence,
            "parser_metadata": {
                "current_board_used_cache": current_parse_result.used_cache,
                "solved_board_used_cache": solved_parse_result.used_cache,
                "model_name": solved_parse_result.model_name,
            },
        },
    )


# Save one compact JSON run report for the latest guarded workflow attempt.
def save_run_report(config: AppConfig, result: ElectricityRunResult) -> None:
    write_json_file(
        config.paths.run_report_file,
        {
            "run_id": result.run_id,
            "started_at": result.started_at,
            "ended_at": result.ended_at,
            "success": result.success,
            "reset_used": result.reset_used,
            "max_rotations": result.max_rotations,
            "planned_rotations": result.planned_rotations,
            "executed_rotations": result.executed_rotations,
            "guard_triggered": result.guard_triggered,
            "completion_flag": result.completion_flag,
            "error_summary": result.error_summary,
            "parser_used_cache_for_current": result.parser_used_cache_for_current,
            "parser_used_cache_for_solved": result.parser_used_cache_for_solved,
            "parser_used_cache_for_final": result.parser_used_cache_for_final,
            "diagnostic_run_dir": result.diagnostic_run_dir,
            "rotation_sequence_planned": result.rotation_sequence_planned,
            "rotation_sequence_executed": result.rotation_sequence_executed,
            "current_board_map": result.current_board_map,
            "solved_board_map": result.solved_board_map,
            "final_board_map": result.final_board_map,
        },
    )


# Return the per-run diagnostics directory used for before/after parser snapshots.
def get_diagnostic_run_dir(config: AppConfig, run_id: str) -> Path:
    return config.paths.output_dir / "diagnostics" / run_id


# Save one parser snapshot phase without letting later workflow steps overwrite it.
def save_parse_snapshot(
    *,
    config: AppConfig,
    run_id: str,
    phase_name: str,
    parse_result: BoardParseResult,
    source_image_response: HubImageResponse,
) -> None:
    phase_dir = get_diagnostic_run_dir(config, run_id) / phase_name
    tiles_dir = phase_dir / "tiles"
    tiles_dir.mkdir(parents=True, exist_ok=True)

    source_image_path = phase_dir / parse_result.image_path.name
    source_image_path.write_bytes(source_image_response.content)

    for tile_result in parse_result.tile_results:
        shutil.copy2(tile_result.crop_path, tiles_dir / tile_result.crop_path.name)

    for artifact_path in build_parser_artifact_candidates(config, parse_result):
        if artifact_path.exists():
            shutil.copy2(artifact_path, phase_dir / artifact_path.name)

    write_json_file(
        phase_dir / "parser_snapshot.json",
        {
            "run_id": run_id,
            "phase": phase_name,
            "saved_at": current_timestamp(),
            "image_path": str(parse_result.image_path),
            "source_sha256": parse_result.source_sha256,
            "model_name": parse_result.model_name,
            "used_cache": parse_result.used_cache,
            "cache_file": str(parse_result.cache_file),
            "board_map": parse_result.board.to_label_map(),
            "tile_results": [
                tile_result_to_record(tile_result)
                for tile_result in parse_result.tile_results
            ],
        },
    )


# Return the parser artifacts that should be frozen for one parse result snapshot.
def build_parser_artifact_candidates(
    config: AppConfig,
    parse_result: BoardParseResult,
) -> tuple[Path, ...]:
    image_stem = parse_result.image_path.stem
    return (
        parse_result.cache_file,
        config.paths.cache_dir / f"{image_stem}_tile_payloads.json",
        config.paths.cache_dir / f"{image_stem}_board_crop.png",
        config.paths.cache_dir / f"{image_stem}_board_detection.json",
    )


# Convert one parsed tile result into one stable JSON-friendly diagnostics record.
def tile_result_to_record(tile_result: ParsedTileResult) -> dict[str, Any]:
    return {
        "coordinate": tile_result.coordinate.label,
        "exits": tile_result.tile.to_exit_names(),
        "confidence": tile_result.confidence,
        "attempts_used": tile_result.attempts_used,
        "crop_path": str(tile_result.crop_path),
        "raw_payload": tile_result.raw_payload,
    }


# Build a concise error summary for guarded partial runs without a completion flag.
def build_error_summary(
    rotation_plan: BoardRotationPlan,
    executed_sequence: list[str],
    completion_flag: str | None,
) -> str | None:
    if completion_flag is not None:
        return None
    if not rotation_plan.rotation_sequence:
        return "Board already matches the solved layout, but the hub did not return a flag during this guarded run."
    if len(executed_sequence) < rotation_plan.total_rotations:
        return (
            "Guarded run stopped before exhausting the planned rotation sequence. "
            f"Executed {len(executed_sequence)} of {rotation_plan.total_rotations} planned rotations."
        )

    return "Rotation batch completed without receiving a final flag."


# Extract a course flag from the verifier response payload or raw text.
def extract_flag(response: HubVerifyResponse) -> str | None:
    return extract_flag_from_value(response.payload) or extract_flag_from_value(response.text)


# Recursively search strings, dicts, and lists for a course flag.
def extract_flag_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        match = FLAG_PATTERN.search(value)
        return match.group(0) if match else None

    if isinstance(value, dict):
        for nested_value in value.values():
            flag = extract_flag_from_value(nested_value)
            if flag:
                return flag

    if isinstance(value, list):
        for nested_value in value:
            flag = extract_flag_from_value(nested_value)
            if flag:
                return flag

    return None


# Add one run identifier to a log record before it is written to disk.
def with_run_id(record: dict[str, Any], run_id: str) -> dict[str, Any]:
    return {"run_id": run_id, **record}


# Return one compact UTC timestamp for reports and run IDs.
def current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


# Build one readable run identifier that also sorts chronologically.
def build_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
