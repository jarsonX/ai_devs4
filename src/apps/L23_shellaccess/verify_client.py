# Guarded Hub client that executes narrowly scoped remote shell commands.

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import requests

from src.apps.L23_shellaccess.config import HubConfig


FLAG_PREFIX = "".join(chr(value) for value in (70, 76, 71))
FLAG_PATTERN = re.compile(r"\{" + FLAG_PREFIX + r":[^}]+\}")


# Store one remote command result without the secret-bearing request payload.
@dataclass(frozen=True)
class CommandResult:
    command_name: str
    status_code: int
    payload: Any
    text: str

    # Return the shell output or fail on an unexpected Hub response.
    def output(self) -> str:
        if self.status_code != 200:
            raise ValueError(f"Hub HTTP status was {self.status_code}.")
        if not isinstance(self.payload, dict) or self.payload.get("code") != 100:
            raise ValueError(f"Hub did not report command success for {self.command_name}.")
        output = self.payload.get("output")
        if not isinstance(output, str):
            raise ValueError("Hub command response has no text output.")
        return output


# Detect a course flag anywhere in the raw or decoded response.
def response_contains_flag(result: CommandResult) -> bool:
    combined = f"{result.text}\n{json.dumps(result.payload, ensure_ascii=False)}"
    return FLAG_PATTERN.search(combined) is not None


# Send remote commands with an explicit request-count guard.
class ShellAccessClient:
    # Store connection settings and initialize the request counter.
    def __init__(self, config: HubConfig, *, timeout_seconds: int, max_requests: int) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds
        self.max_requests = max_requests
        self.session = requests.Session()
        self.request_count = 0

    # Execute one named command without logging the API key.
    def execute(self, command: str, *, command_name: str) -> CommandResult:
        self.request_count += 1
        if self.request_count > self.max_requests:
            raise ValueError("The Hub request guard was exceeded.")
        response = self.session.post(
            self.config.verify_url,
            json={
                "apikey": self.config.api_key,
                "task": self.config.task_name,
                "answer": {"cmd": command},
            },
            timeout=self.timeout_seconds,
        )
        try:
            payload: Any = response.json()
        except requests.JSONDecodeError:
            payload = None
        return CommandResult(command_name, response.status_code, payload, response.text)
