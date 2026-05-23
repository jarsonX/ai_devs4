# HTTP client helpers for the L7 electricity Hub workflow.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests

from src.apps.L7_electricity.config import HubConfig
from src.apps.L7_electricity.models import Coordinate


REQUEST_TIMEOUT_SECONDS = 30
REDACTED = "***REDACTED***"


# Store one downloaded image response together with transport metadata.
@dataclass(frozen=True)
class HubImageResponse:
    status_code: int
    content: bytes
    content_type: str | None
    headers: dict[str, str]


# Store one decoded verify response together with raw text and headers.
@dataclass(frozen=True)
class HubVerifyResponse:
    status_code: int
    payload: Any | None
    text: str
    headers: dict[str, str]


# Build the current-board data URL expected by the Hub.
def build_current_board_url(config: HubConfig, reset: bool = False) -> str:
    base_url = config.data_base_url.rstrip("/")
    image_url = f"{base_url}/{config.api_key}/{config.task_name}.png"
    if not reset:
        return image_url

    return f"{image_url}?{urlencode({'reset': '1'})}"


# Build the exact payload expected by the Hub electricity verifier.
def build_rotate_payload(config: HubConfig, coordinate_label: str) -> dict[str, Any]:
    normalized_label = Coordinate.from_label(coordinate_label).label
    return {
        "apikey": config.api_key,
        "task": config.task_name,
        "answer": {
            "rotate": normalized_label,
        },
    }


# Mask secret fields before writing request payloads to logs or reports.
def mask_payload_for_storage(payload: dict[str, Any]) -> dict[str, Any]:
    masked_payload = dict(payload)
    masked_payload["apikey"] = REDACTED
    return masked_payload


# Convert an HTTP image response into a small serializable object.
def build_image_response(response: requests.Response) -> HubImageResponse:
    return HubImageResponse(
        status_code=response.status_code,
        content=response.content,
        content_type=response.headers.get("Content-Type"),
        headers=dict(response.headers.items()),
    )


# Convert an HTTP verify response into a small object with JSON fallback.
def build_verify_response(response: requests.Response) -> HubVerifyResponse:
    try:
        payload = response.json()
    except requests.JSONDecodeError:
        payload = None

    return HubVerifyResponse(
        status_code=response.status_code,
        payload=payload,
        text=response.text,
        headers=dict(response.headers.items()),
    )


# Communicate with the Hub endpoints required by the electricity workflow.
class HubClient:
    # Store Hub configuration and an injectable HTTP session.
    def __init__(
        self,
        config: HubConfig,
        session: requests.Session | None = None,
        timeout_seconds: int = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self.config = config
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds

    # Download the current board PNG, optionally resetting the puzzle first.
    def download_current_board(self, reset: bool = False) -> HubImageResponse:
        response = self.session.get(
            build_current_board_url(self.config, reset=reset),
            timeout=self.timeout_seconds,
        )
        return build_image_response(response)

    # Download the solved reference board PNG from the configured location.
    def download_solved_board(self) -> HubImageResponse:
        response = self.session.get(
            self.config.solved_image_url,
            timeout=self.timeout_seconds,
        )
        return build_image_response(response)

    # Submit one clockwise tile rotation request to the Hub verifier.
    def rotate_tile_once(self, coordinate_label: str) -> HubVerifyResponse:
        response = self.session.post(
            self.config.verify_url,
            json=build_rotate_payload(self.config, coordinate_label),
            timeout=self.timeout_seconds,
        )
        return build_verify_response(response)
