# Strict agent tools and guarded dispatch for the firmware workbench.

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping, cast

from openai.types.responses.function_tool_param import FunctionToolParam
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from src.apps.L12_firmware.config import AppConfig
from src.apps.L12_firmware.guards import (
    BASH_HISTORY_FILE,
    SETTINGS_FILE,
    CommandDecision,
    FirmwareGuardState,
    validate_confirmation_submission,
    validate_shell_command,
)
from src.apps.L12_firmware.hub_client import HubClient
from src.apps.L12_firmware.http_client import ApiResponse
from src.apps.L12_firmware.repair_planner import (
    FIRMWARE_DIRECTORY,
    LOCK_FILE,
    SETTINGS_FILE as PLANNER_SETTINGS_FILE,
    build_repair_plan,
)
from src.apps.L12_firmware.shell_client import ShellClient


# Validate one model-requested restricted shell command.
class RunShellCommandArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: str = Field(min_length=1, max_length=300)

    # Normalize harmless surrounding whitespace before command policy checks.
    @field_validator("command", mode="before")
    @classmethod
    def validate_command(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("command must not be empty.")
        return cleaned_value


# Validate one model-requested firmware confirmation submission.
class SubmitAnswerArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation: str = Field(pattern=r"^ECCS-[A-Za-z0-9]{40}$")

    # Normalize harmless surrounding whitespace before provenance checks.
    @field_validator("confirmation", mode="before")
    @classmethod
    def validate_confirmation(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        return value.strip()


# Store one stable tool result for model feedback and local tests.
@dataclass(frozen=True)
class FirmwareToolResult:
    tool_name: str
    ok: bool
    payload: dict[str, Any]
    terminal: bool = False
    solved: bool = False

    # Convert the result into a compact JSON-ready dictionary.
    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "ok": self.ok,
            "payload": self.payload,
            "terminal": self.terminal,
            "solved": self.solved,
        }


# Normalize a Pydantic schema into OpenAI strict function-tool requirements.
def build_openai_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    normalized_schema = dict(schema)

    if normalized_schema.get("type") == "object":
        properties = normalized_schema.get("properties", {})
        if isinstance(properties, dict):
            normalized_schema["properties"] = {
                key: build_openai_strict_schema(value)
                if isinstance(value, dict)
                else value
                for key, value in properties.items()
            }
            normalized_schema["required"] = list(properties.keys())
        normalized_schema["additionalProperties"] = False

    items = normalized_schema.get("items")
    if isinstance(items, dict):
        normalized_schema["items"] = build_openai_strict_schema(items)

    for keyword in ("anyOf", "allOf", "oneOf"):
        values = normalized_schema.get(keyword)
        if isinstance(values, list):
            normalized_schema[keyword] = [
                build_openai_strict_schema(value)
                if isinstance(value, dict)
                else value
                for value in values
            ]

    for defs_key in ("$defs", "definitions"):
        defs_value = normalized_schema.get(defs_key)
        if isinstance(defs_value, dict):
            normalized_schema[defs_key] = {
                key: build_openai_strict_schema(value)
                if isinstance(value, dict)
                else value
                for key, value in defs_value.items()
            }

    return normalized_schema


# Return only the strict tools permitted for the current run mode.
def build_tool_definitions(
    *,
    submission_enabled: bool,
) -> list[FunctionToolParam]:
    tools: list[FunctionToolParam] = [
        cast(
            FunctionToolParam,
            {
                "type": "function",
                "name": "run_shell_command",
                "description": (
                    "Run one command through the restricted firmware shell. "
                    "The backend enforces allowed commands, paths, .gitignore rules, "
                    "write scope, and executable scope."
                ),
                "parameters": build_openai_strict_schema(
                    RunShellCommandArgs.model_json_schema()
                ),
                "strict": True,
            },
        ),
    ]
    if submission_enabled:
        tools.append(
            cast(
            FunctionToolParam,
            {
                "type": "function",
                "name": "submit_answer",
                "description": (
                    "Submit the final ECCS confirmation code. "
                    "The backend allows only a correctly shaped code observed in shell output."
                ),
                "parameters": build_openai_strict_schema(
                    SubmitAnswerArgs.model_json_schema()
                ),
                "strict": True,
            },
            )
        )
    return tools


# Return one stable validation or dispatch error for the model.
def build_error_result(
    tool_name: str,
    *,
    code: str,
    message: str,
    recovery_hint: str,
    terminal: bool = False,
) -> FirmwareToolResult:
    return FirmwareToolResult(
        tool_name=tool_name,
        ok=False,
        terminal=terminal,
        payload={
            "error": {
                "code": code,
                "message": message,
                "recovery_hint": recovery_hint,
            }
        },
    )


# Convert the shared API response into a bounded model-facing payload.
def build_api_result_payload(
    response: ApiResponse,
    *,
    max_chars: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": response.ok,
        "status_code": response.status_code,
        "payload": response.payload,
        "text": response.text,
    }
    if response.error is not None:
        result["error"] = {
            "code": response.error.code,
            "message": response.error.message,
            "retryable": response.error.retryable,
            "recovery_hint": response.error.recovery_hint,
            "retry_after_seconds": response.error.retry_after_seconds,
        }
    serialized_result = json.dumps(result, ensure_ascii=False, default=str)
    if len(serialized_result) <= max_chars:
        return result

    compact_result: dict[str, Any] = {
        "ok": response.ok,
        "status_code": response.status_code,
        "truncated": True,
    }
    if response.error is not None:
        compact_result["error"] = {
            "code": response.error.code,
            "retryable": response.error.retryable,
            "recovery_hint": response.error.recovery_hint,
        }
    overhead = len(json.dumps(compact_result, ensure_ascii=False, default=str))
    preview_budget = max(0, max_chars - overhead - 40)
    compact_result["preview"] = serialized_result[:preview_budget]
    return compact_result


# Return the most useful application data field from one decoded API payload.
def extract_response_data(payload: Any) -> Any:
    if isinstance(payload, Mapping) and "data" in payload:
        return payload["data"]
    return payload


# Extract a canonical pwd path from common shell response shapes.
def extract_pwd_path(payload: Any, text: str) -> str | None:
    data = extract_response_data(payload)
    candidates: list[str] = []
    if isinstance(data, str):
        candidates.append(data)
    elif isinstance(data, Mapping):
        for field_name in ("pwd", "cwd", "path", "output", "result"):
            value = data.get(field_name)
            if isinstance(value, str):
                candidates.append(value)
    candidates.append(text)

    for candidate in candidates:
        for line in candidate.splitlines():
            cleaned_line = line.strip()
            if cleaned_line.startswith("/"):
                return cleaned_line
    return None


# Extract listed entry names from common shell response shapes.
def extract_listing_entries(payload: Any) -> list[str] | None:
    data = extract_response_data(payload)
    if isinstance(data, Mapping):
        for field_name in ("entries", "files", "items", "output", "result"):
            if field_name in data:
                data = data[field_name]
                break
    if isinstance(data, list):
        entries: list[str] = []
        for item in data:
            if isinstance(item, str) and item.strip():
                entries.append(item.strip())
            elif isinstance(item, Mapping):
                for field_name in ("name", "path"):
                    value = item.get(field_name)
                    if isinstance(value, str) and value.strip():
                        entries.append(value.strip())
                        break
        return entries
    if isinstance(data, str):
        return [line.strip() for line in data.splitlines() if line.strip()]
    return None


# Extract file text from common cat response shapes.
def extract_file_content(payload: Any, text: str) -> str | None:
    data = extract_response_data(payload)
    if isinstance(data, str):
        return data
    if isinstance(data, list) and all(isinstance(item, str) for item in data):
        return "\n".join(data)
    if isinstance(data, Mapping):
        for field_name in ("content", "output", "result", "text"):
            value = data.get(field_name)
            if isinstance(value, str):
                return value
            if isinstance(value, list) and all(
                isinstance(item, str) for item in value
            ):
                return "\n".join(value)
    return text or None


# Detect course success without exposing flag contents in the result summary.
def response_contains_flag(value: Any) -> bool:
    if isinstance(value, str):
        return "{FLG:" in value and "}" in value
    if isinstance(value, Mapping):
        return any(response_contains_flag(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(response_contains_flag(item) for item in value)
    return False


# Own tool-side state updates, validation, and client dispatch.
class FirmwareToolbox:
    # Wire bounded clients and guard state into one model-facing tool layer.
    def __init__(
        self,
        config: AppConfig,
        shell_client: ShellClient,
        *,
        hub_client: HubClient | None = None,
        submission_enabled: bool = False,
    ) -> None:
        self.config = config
        self.shell_client = shell_client
        self.hub_client = hub_client
        self.submission_enabled = submission_enabled
        self.state = FirmwareGuardState()
        self.tool_call_count = 0
        self.last_shell_response: ApiResponse | None = None
        self.last_submission_response: ApiResponse | None = None
        self.last_confirmation: str | None = None
        self.shell_history: list[dict[str, Any]] = []
        self.submission_history: list[dict[str, Any]] = []

    # Validate and dispatch one of the two supported model tools.
    def dispatch_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> FirmwareToolResult:
        self.tool_call_count += 1
        try:
            if tool_name == "run_shell_command":
                parsed_arguments = RunShellCommandArgs.model_validate(arguments)
                return self._run_shell_command(parsed_arguments)
            if tool_name == "submit_answer":
                parsed_arguments = SubmitAnswerArgs.model_validate(arguments)
                return self._submit_answer(parsed_arguments)
        except ValidationError as error:
            return build_error_result(
                tool_name,
                code="invalid_tool_arguments",
                message=str(error),
                recovery_hint="Call the tool again with only the required valid fields.",
            )

        return build_error_result(
            tool_name,
            code="unknown_tool",
            message=f"Unsupported tool: {tool_name}.",
            recovery_hint="Use run_shell_command or submit_answer.",
        )

    # Validate, execute, and record one restricted shell command.
    def _run_shell_command(
        self,
        arguments: RunShellCommandArgs,
    ) -> FirmwareToolResult:
        decision = validate_shell_command(
            arguments.command,
            self.state,
            max_command_chars=self.config.runtime.max_command_chars,
        )
        if not decision.allowed:
            return self._blocked_command_result(decision)

        masked_request, response = self.shell_client.run_command(
            decision.normalized_command or arguments.command
        )
        self.last_shell_response = response
        self.shell_history.append(
            {
                "request": masked_request,
                "response": response.to_dict(),
            }
        )
        response_payload = build_api_result_payload(
            response,
            max_chars=self.config.runtime.max_shell_result_chars,
        )
        if not response.ok:
            error_code = response.error.code if response.error else "shell_api_error"
            return FirmwareToolResult(
                tool_name="run_shell_command",
                ok=False,
                terminal=error_code == "request_limit_reached",
                payload={
                    "decision": command_decision_to_dict(decision),
                    "request": masked_request,
                    "response": response_payload,
                    "state": self.build_state_summary(),
                },
            )

        state_error = self._apply_successful_shell_state(decision, response)
        discovered_codes = self.state.record_shell_observation(
            {"payload": response.payload, "text": response.text}
        )
        if discovered_codes:
            self.last_confirmation = sorted(discovered_codes)[0]
        return FirmwareToolResult(
            tool_name="run_shell_command",
            ok=state_error is None,
            payload={
                "decision": command_decision_to_dict(decision),
                "request": masked_request,
                "response": response_payload,
                "discovered_confirmation_count": len(discovered_codes),
                "state_update_error": state_error,
                "state": self.build_state_summary(),
            },
        )

    # Validate provenance and submit one final confirmation code.
    def _submit_answer(
        self,
        arguments: SubmitAnswerArgs,
    ) -> FirmwareToolResult:
        if not self.submission_enabled or self.hub_client is None:
            return build_error_result(
                "submit_answer",
                code="submission_disabled",
                message="Hub submission is disabled for this run.",
                recovery_hint="Stop without submitting or restart with explicit submission enabled.",
                terminal=True,
            )

        decision = validate_confirmation_submission(
            arguments.confirmation,
            self.state,
        )
        if not decision.allowed:
            return build_error_result(
                "submit_answer",
                code=decision.code,
                message=decision.message,
                recovery_hint="Continue shell investigation and submit only an observed code.",
            )

        masked_request, response = self.hub_client.submit_confirmation(
            decision.confirmation or arguments.confirmation
        )
        self.last_submission_response = response
        self.last_confirmation = decision.confirmation
        self.submission_history.append(
            {
                "request": masked_request,
                "response": response.to_dict(),
            }
        )
        accepted = response.ok and (
            response_contains_flag(response.payload)
            or response_contains_flag(response.text)
        )
        response_payload = build_api_result_payload(
            response,
            max_chars=self.config.runtime.max_shell_result_chars,
        )
        if isinstance(response_payload.get("payload"), dict):
            response_payload["payload"] = {
                **response_payload["payload"],
                "flag_found": accepted,
            }

        return FirmwareToolResult(
            tool_name="submit_answer",
            ok=accepted,
            terminal=True,
            solved=accepted,
            payload={
                "request": masked_request,
                "response": response_payload,
                "accepted": accepted,
                "confirmation_grounded": True,
            },
        )

    # Convert one blocked command decision into model-facing recovery guidance.
    def _blocked_command_result(
        self,
        decision: CommandDecision,
    ) -> FirmwareToolResult:
        return build_error_result(
            "run_shell_command",
            code=decision.code,
            message=decision.message,
            recovery_hint=decision.recovery_hint or "Choose another allowed command.",
        )

    # Apply command-specific state changes after one successful shell response.
    def _apply_successful_shell_state(
        self,
        decision: CommandDecision,
        response: ApiResponse,
    ) -> str | None:
        command = decision.normalized_command or ""
        command_name = command.split(maxsplit=1)[0] if command else ""
        try:
            if command_name == "pwd":
                pwd_path = extract_pwd_path(response.payload, response.text)
                if pwd_path is None:
                    return "pwd response did not contain an absolute path."
                self.state.record_current_directory(pwd_path)
            elif command_name == "ls" and decision.resolved_path:
                entries = extract_listing_entries(response.payload)
                if entries is None:
                    return "ls response did not contain a recognizable entry list."
                self.state.record_directory_listing(decision.resolved_path, entries)
            elif command_name == "cd" and decision.resolved_path:
                self.state.record_current_directory(decision.resolved_path)
            elif command_name == "cat" and decision.resolved_path:
                resolved_path = PurePosixPath(decision.resolved_path)
                if resolved_path.name in {
                    ".gitignore",
                    SETTINGS_FILE.name,
                    BASH_HISTORY_FILE.name,
                }:
                    content = extract_file_content(response.payload, response.text)
                    if content is None:
                        return "cat response did not contain recognizable file content."
                    if resolved_path.name == ".gitignore":
                        self.state.record_gitignore(resolved_path.parent, content)
                    elif resolved_path == SETTINGS_FILE:
                        self.state.record_file_snapshot(resolved_path, content)
                    elif resolved_path == BASH_HISTORY_FILE:
                        self.state.record_firmware_history(content)
            elif command_name == "editline" and decision.resolved_path:
                command_parts = command.split(maxsplit=3)
                if len(command_parts) < 4:
                    return "editline command state update could not parse line number and replacement."
                self.state.record_successful_edit(
                    decision.resolved_path,
                    line_number=int(command_parts[2]),
                    replacement_content=command_parts[3],
                )
            elif command_name == "rm" and decision.resolved_path:
                self.state.record_removed_path(decision.resolved_path)
            elif command_name == "reboot":
                self.state.reset()
        except ValueError as error:
            return str(error)
        return None

    # Return compact state without exposing file content or confirmation values.
    def build_state_summary(self) -> dict[str, Any]:
        fresh_settings_snapshot = self.state.file_snapshots.get(PLANNER_SETTINGS_FILE)
        projected_settings_snapshot = self.state.projected_file_snapshots.get(
            PLANNER_SETTINGS_FILE
        )
        settings_snapshot = fresh_settings_snapshot or projected_settings_snapshot
        firmware_directory_entries = self.state.directory_entries.get(FIRMWARE_DIRECTORY)
        repair_plan = build_repair_plan(
            settings_snapshot=settings_snapshot,
            settings_snapshot_fresh=fresh_settings_snapshot is not None,
            firmware_directory_entries=firmware_directory_entries,
            password_candidate_counts=self.state.firmware_password_candidate_counts,
        )
        return {
            "current_directory": (
                str(self.state.current_directory)
                if self.state.current_directory is not None
                else None
            ),
            "inspected_directories": sorted(
                str(path) for path in self.state.inspected_directories
            ),
            "pending_gitignore_directories": sorted(
                str(path) for path in self.state.pending_gitignore_directories
            ),
            "settings_snapshot_loaded": SETTINGS_FILE in self.state.file_snapshots,
            "settings_snapshot_projected": (
                fresh_settings_snapshot is None and projected_settings_snapshot is not None
            ),
            "observed_confirmation_count": len(
                self.state.observed_confirmation_codes
            ),
            "grounded_password_candidate_count": sum(
                count >= 2
                for count in self.state.firmware_password_candidate_counts.values()
            ),
            "lock_file_observed": LOCK_FILE.name in (firmware_directory_entries or ()),
            "repair_plan": repair_plan.to_dict(),
            "tool_calls_used": self.tool_call_count,
        }

    # Return complete course runtime data for the ignored human-inspection report.
    def build_runtime_report(self) -> dict[str, Any]:
        return {
            "state": {
                **self.build_state_summary(),
                "observed_confirmation_codes": sorted(
                    self.state.observed_confirmation_codes
                ),
            },
            "shell_history": list(self.shell_history),
            "submission_history": list(self.submission_history),
            "last_confirmation": self.last_confirmation,
        }


# Convert a command decision into a stable JSON-ready payload.
def command_decision_to_dict(decision: CommandDecision) -> dict[str, Any]:
    return {
        "allowed": decision.allowed,
        "code": decision.code,
        "message": decision.message,
        "normalized_command": decision.normalized_command,
        "resolved_path": decision.resolved_path,
        "recovery_hint": decision.recovery_hint,
    }
