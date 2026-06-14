# Guarded Hub transport for one-command reactor requests.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from src.apps.L13_reactor.config import HubConfig


REDACTED = "***REDACTED***"
ALLOWED_COMMANDS = frozenset({"start", "reset", "left", "wait", "right"})


# Preserve one Hub response without losing non-JSON feedback.
@dataclass(frozen=True)
class HubResponse:
    status_code: int
    payload: Any
    text: str


# Stop the controller before it can exceed its approved command budget.
class CommandGuard:
    # Store a strict command cap for the current reactor run.
    def __init__(self, max_commands: int) -> None:
        if max_commands < 1:
            raise ValueError("max_commands must be positive.")
        self.max_commands = max_commands
        self.used_commands = 0

    # Count one planned request and reject calls after the cap.
    def consume(self) -> int:
        if self.used_commands >= self.max_commands:
            raise RuntimeError(
                f"Reactor command guard reached {self.max_commands} calls."
            )
        self.used_commands += 1
        return self.used_commands


# Build the exact one-command payload expected by the reactor task.
def build_command_payload(config: HubConfig, command: str) -> dict[str, Any]:
    normalized_command = command.strip().lower()
    if normalized_command not in ALLOWED_COMMANDS:
        raise ValueError(f"Unsupported reactor command: {command!r}.")
    return {
        "apikey": config.api_key,
        "task": config.task_name,
        "answer": {
            "command": normalized_command,
        },
    }


# Remove the API key before preserving a request in runtime logs.
def mask_payload_for_storage(payload: dict[str, Any]) -> dict[str, Any]:
    masked_payload = dict(payload)
    if "apikey" in masked_payload:
        masked_payload["apikey"] = REDACTED
    return masked_payload


# Convert an HTTP response into the stable internal response shape.
def build_hub_response(response: requests.Response) -> HubResponse:
    try:
        payload = response.json()
    except requests.JSONDecodeError:
        payload = None
    return HubResponse(
        status_code=response.status_code,
        payload=payload,
        text=response.text,
    )


# Submit reactor commands through one guarded HTTP session.
class HubClient:
    # Store Hub config plus injectable HTTP dependencies for tests.
    def __init__(
        self,
        config: HubConfig,
        *,
        timeout_seconds: int,
        guard: CommandGuard,
        session: requests.Session | None = None,
    ) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds
        self.guard = guard
        self.session = session or requests.Session()

    # Send one validated command and return masked request plus full response.
    def send_command(
        self,
        command: str,
    ) -> tuple[int, dict[str, Any], HubResponse]:
        sequence = self.guard.consume()
        payload = build_command_payload(self.config, command)
        response = self.session.post(
            self.config.verify_url,
            json=payload,
            timeout=self.timeout_seconds,
        )
        return sequence, mask_payload_for_storage(payload), build_hub_response(response)
