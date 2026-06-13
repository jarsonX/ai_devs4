# Guarded HTTP client for the restricted firmware shell API.

from __future__ import annotations

from typing import Any

import requests

from src.apps.L12_firmware.config import (
    ExternalApiConfig,
    MAX_SHELL_REQUESTS,
    REQUEST_TIMEOUT_SECONDS,
)
from src.apps.L12_firmware.http_client import ApiResponse, RequestGuard, post_json


REDACTED = "***REDACTED***"


# Build the exact request payload expected by the restricted shell API.
def build_shell_payload(
    config: ExternalApiConfig,
    command: str,
) -> dict[str, str]:
    return {
        "apikey": config.api_key,
        "cmd": command,
    }


# Mask the API key before shell payloads are stored in runtime reports.
def mask_shell_payload(payload: dict[str, Any]) -> dict[str, Any]:
    masked_payload = dict(payload)
    if "apikey" in masked_payload:
        masked_payload["apikey"] = REDACTED
    return masked_payload


# Send bounded commands to the restricted virtual machine shell.
class ShellClient:
    # Store shell configuration, an injectable session, and its request guard.
    def __init__(
        self,
        config: ExternalApiConfig,
        *,
        session: requests.Session | Any | None = None,
        timeout_seconds: int = REQUEST_TIMEOUT_SECONDS,
        guard: RequestGuard | None = None,
    ) -> None:
        self.config = config
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds
        self.guard = guard or RequestGuard(MAX_SHELL_REQUESTS)

    # Send one command after later workflow layers approve its content.
    def run_command(self, command: str) -> tuple[dict[str, Any], ApiResponse]:
        payload = build_shell_payload(self.config, command)
        response = post_json(
            session=self.session,
            url=self.config.shell_url,
            payload=payload,
            timeout_seconds=self.timeout_seconds,
            guard=self.guard,
        )
        return mask_shell_payload(payload), response
