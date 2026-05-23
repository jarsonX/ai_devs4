# Save masked L7 electricity workflow artifacts for later review.

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.apps.L7_electricity.config import AppPaths, HubConfig
from src.apps.L7_electricity.hub_client import (
    HubImageResponse,
    HubVerifyResponse,
    build_rotate_payload,
    mask_payload_for_storage,
)


# Return one timezone-aware timestamp string for saved artifacts.
def current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


# Append one JSON record to a JSONL file using stable UTF-8 formatting.
def append_jsonl_record(file_path: Path, record: dict[str, Any]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    serialized_record = json.dumps(record, ensure_ascii=False)
    with file_path.open("a", encoding="utf-8") as handle:
        handle.write(serialized_record)
        handle.write("\n")


# Save one JSON artifact with pretty formatting for manual inspection.
def write_json_file(file_path: Path, payload: dict[str, Any]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# Build one masked request record for downloading the current board image.
def build_current_board_request_record(reset: bool) -> dict[str, Any]:
    return {
        "timestamp": current_timestamp(),
        "kind": "download_current_board",
        "method": "GET",
        "url_config": "HUB_DATA_BASE_URL",
        "task": "electricity",
        "query": {"reset": "1"} if reset else {},
    }


# Build one masked request record for downloading the solved reference image.
def build_solved_board_request_record() -> dict[str, Any]:
    return {
        "timestamp": current_timestamp(),
        "kind": "download_solved_board",
        "method": "GET",
        "url_config": "HUB_SOLVED_IMAGE_URL",
        "task": "electricity",
        "query": {},
    }


# Build one masked request record for a single clockwise rotation request.
def build_rotate_request_record(config: HubConfig, coordinate_label: str) -> dict[str, Any]:
    return {
        "timestamp": current_timestamp(),
        "kind": "rotate_tile_once",
        "method": "POST",
        "url_config": "HUB_VERIFY_URL",
        "payload": mask_payload_for_storage(
            build_rotate_payload(config, coordinate_label)
        ),
    }


# Build one response record for a downloaded board image without storing binary bytes.
def build_image_response_record(
    response: HubImageResponse,
    *,
    kind: str,
) -> dict[str, Any]:
    return {
        "timestamp": current_timestamp(),
        "kind": kind,
        "http_status": response.status_code,
        "content_type": response.content_type,
        "content_length": len(response.content),
        "headers": response.headers,
    }


# Build one response record for a verifier call.
def build_verify_response_record(
    response: HubVerifyResponse,
    *,
    kind: str,
    coordinate_label: str,
) -> dict[str, Any]:
    return {
        "timestamp": current_timestamp(),
        "kind": kind,
        "coordinate": coordinate_label,
        "http_status": response.status_code,
        "payload": response.payload,
        "text": response.text,
        "headers": response.headers,
    }


# Append one masked request record to the configured request log.
def append_request_log(paths: AppPaths, record: dict[str, Any]) -> None:
    append_jsonl_record(paths.request_log_file, record)


# Append one response record to the configured response log.
def append_response_log(paths: AppPaths, record: dict[str, Any]) -> None:
    append_jsonl_record(paths.response_log_file, record)
