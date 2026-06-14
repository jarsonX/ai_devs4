# Bounded command loop for the deterministic L13 reactor controller.

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

from src.apps.L13_reactor.config import AppConfig, ensure_runtime_directories
from src.apps.L13_reactor.hub_client import CommandGuard, HubClient, HubResponse
from src.apps.L13_reactor.models import ReactorState, WorkflowResult
from src.apps.L13_reactor.run_log import append_command_event, create_run_log_path
from src.apps.L13_reactor.state_parser import parse_reactor_state
from src.apps.L13_reactor.strategy import choose_command


FLAG_PATTERN = re.compile(r"\{FLG:[^}]+}")


# Define the narrow transport contract used by the workflow and local tests.
class HubClientProtocol(Protocol):
    # Send one command and return its sequence, masked request, and response.
    def send_command(
        self,
        command: str,
    ) -> tuple[int, dict[str, object], HubResponse]: ...


# Detect a course flag inside nested response values without printing it.
def contains_flag(value: object) -> bool:
    if isinstance(value, str):
        return FLAG_PATTERN.search(value) is not None
    if isinstance(value, dict):
        return any(contains_flag(nested) for nested in value.values())
    if isinstance(value, list):
        return any(contains_flag(nested) for nested in value)
    return False


# Send and log one command before interpreting the resulting payload.
def _execute_command(
    client: HubClientProtocol,
    log_path: Path,
    command: str,
) -> HubResponse:
    sequence, masked_request, response = client.send_command(command)
    append_command_event(
        log_path,
        sequence=sequence,
        command=command,
        masked_request=masked_request,
        response=response,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Hub returned HTTP {response.status_code} for reactor command {command!r}."
        )
    return response


# Run the controller until success or a deterministic guard stops it.
def run_reactor_workflow(
    config: AppConfig,
    *,
    client: HubClientProtocol | None = None,
    log_path: Path | None = None,
) -> WorkflowResult:
    ensure_runtime_directories(config.paths)
    active_log_path = log_path or create_run_log_path(config.paths.logs_dir)
    active_client = client or HubClient(
        config.hub,
        timeout_seconds=config.runtime.request_timeout_seconds,
        guard=CommandGuard(config.runtime.max_commands),
    )

    response = _execute_command(active_client, active_log_path, "start")
    commands_sent = 1
    flag_found = contains_flag(response.payload) or contains_flag(response.text)
    if flag_found:
        return WorkflowResult(
            completed=True,
            commands_sent=commands_sent,
            final_player_column=config.runtime.goal_column,
            final_player_row=config.runtime.robot_row,
            final_message="Hub accepted the reactor task.",
            log_path=str(active_log_path.relative_to(config.paths.repo_root)),
            flag_found=True,
        )
    state = parse_reactor_state(response.payload)

    while not state.reached_goal:
        command = choose_command(state)
        response = _execute_command(
            active_client,
            active_log_path,
            command,
        )
        commands_sent += 1
        flag_found = contains_flag(response.payload) or contains_flag(response.text)
        if flag_found:
            return WorkflowResult(
                completed=True,
                commands_sent=commands_sent,
                final_player_column=state.goal_column,
                final_player_row=state.goal_row,
                final_message="Hub accepted the reactor task.",
                log_path=str(active_log_path.relative_to(config.paths.repo_root)),
                flag_found=True,
            )
        state = parse_reactor_state(response.payload)

    return WorkflowResult(
        completed=state.reached_goal,
        commands_sent=commands_sent,
        final_player_column=state.player_column,
        final_player_row=state.player_row,
        final_message=state.message,
        log_path=str(active_log_path.relative_to(config.paths.repo_root)),
        flag_found=False,
    )
