# Load and validate the saved railway help contract.

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.apps.L5_railway.config import AppPaths


EXPECTED_ACTIONS = {
    "reconfigure": ("route",),
    "getstatus": ("route",),
    "setstatus": ("route", "value"),
    "save": ("route",),
}
EXPECTED_SETSTATUS_VALUES = ("RTOPEN", "RTCLOSE")
EXPECTED_STATUS_VALUE_KEYS = ("RTOPEN", "RTCLOSE")


# Store one normalized action definition from the saved help contract.
@dataclass(frozen=True)
class HelpAction:
    name: str
    required_fields: tuple[str, ...]
    optional_fields: tuple[str, ...]
    about: str
    allowed_values: tuple[str, ...] = ()


# Store the validated help contract used by the railway workflow.
@dataclass(frozen=True)
class HelpContract:
    http_status: int
    route_format: str
    status_values: dict[str, str]
    notes: tuple[str, ...]
    actions_by_name: dict[str, HelpAction]


# Load and validate the saved help contract from the default app paths.
def load_help_contract(paths: AppPaths) -> HelpContract:
    return load_help_contract_from_file(paths.help_response_file)


# Load and validate the saved help contract from one JSON file.
def load_help_contract_from_file(file_path: Path) -> HelpContract:
    raw_payload = json.loads(file_path.read_text(encoding="utf-8"))
    return parse_help_contract(raw_payload, source_name=str(file_path))


# Parse one saved help payload and convert it into a normalized contract object.
def parse_help_contract(raw_payload: Any, source_name: str = "help_response.json") -> HelpContract:
    if not isinstance(raw_payload, dict):
        raise ValueError(f"{source_name} must contain a JSON object.")

    http_status = _require_int(raw_payload, "http_status", source_name)
    if http_status != 200:
        raise ValueError(f"{source_name} must contain http_status=200.")

    body = _require_dict(raw_payload, "body", source_name)
    ok_value = body.get("ok")
    if ok_value is not True:
        raise ValueError(f"{source_name} must contain body.ok=true.")

    action_name = body.get("action")
    if action_name != "help":
        raise ValueError(f"{source_name} must contain body.action='help'.")

    help_section = _require_dict(body, "help", source_name)
    route_format = _require_str(help_section, "route_format", source_name)
    status_values = _require_dict(help_section, "status_values", source_name)
    notes = _read_notes(help_section, source_name)
    actions_by_name = _read_actions(help_section, source_name)

    _validate_expected_actions(actions_by_name, source_name)
    _validate_setstatus_values(actions_by_name["setstatus"], source_name)
    _validate_status_value_keys(status_values, source_name)

    return HelpContract(
        http_status=http_status,
        route_format=route_format,
        status_values={str(key): str(value) for key, value in status_values.items()},
        notes=notes,
        actions_by_name=actions_by_name,
    )


# Read and normalize all action entries from the saved help section.
def _read_actions(help_section: dict[str, Any], source_name: str) -> dict[str, HelpAction]:
    raw_actions = help_section.get("actions")
    if not isinstance(raw_actions, list) or not raw_actions:
        raise ValueError(f"{source_name} must contain a non-empty help.actions list.")

    actions_by_name: dict[str, HelpAction] = {}
    for index, raw_action in enumerate(raw_actions):
        if not isinstance(raw_action, dict):
            raise ValueError(f"{source_name} action at index {index} must be an object.")

        action = HelpAction(
            name=_require_str(raw_action, "action", source_name),
            required_fields=_read_string_list(raw_action, "requires", source_name),
            optional_fields=_read_string_list(raw_action, "optional", source_name),
            about=_require_str(raw_action, "about", source_name),
            allowed_values=_read_string_list(raw_action, "allowed_values", source_name, required=False),
        )
        if action.name in actions_by_name:
            raise ValueError(f"{source_name} contains duplicate action '{action.name}'.")

        actions_by_name[action.name] = action

    return actions_by_name


# Read the optional notes list while keeping the output shape stable.
def _read_notes(help_section: dict[str, Any], source_name: str) -> tuple[str, ...]:
    if "notes" not in help_section:
        return ()

    return _read_string_list(help_section, "notes", source_name)


# Validate that the required workflow actions are present with expected fields.
def _validate_expected_actions(actions_by_name: dict[str, HelpAction], source_name: str) -> None:
    for action_name, expected_fields in EXPECTED_ACTIONS.items():
        action = actions_by_name.get(action_name)
        if action is None:
            raise ValueError(f"{source_name} is missing required action '{action_name}'.")

        if action.required_fields != expected_fields:
            raise ValueError(
                f"{source_name} action '{action_name}' requires {action.required_fields}, "
                f"expected {expected_fields}."
            )


# Validate the documented setstatus values needed by the planned workflow.
def _validate_setstatus_values(action: HelpAction, source_name: str) -> None:
    if action.allowed_values != EXPECTED_SETSTATUS_VALUES:
        raise ValueError(
            f"{source_name} action 'setstatus' allowed_values are {action.allowed_values}, "
            f"expected {EXPECTED_SETSTATUS_VALUES}."
        )


# Validate the status value keys expected by the activation flow.
def _validate_status_value_keys(status_values: dict[str, Any], source_name: str) -> None:
    keys = tuple(str(key) for key in status_values.keys())
    if keys != EXPECTED_STATUS_VALUE_KEYS:
        raise ValueError(
            f"{source_name} status_values keys are {keys}, expected {EXPECTED_STATUS_VALUE_KEYS}."
        )


# Read one required string field from a dictionary.
def _require_str(payload: dict[str, Any], field_name: str, source_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{source_name} field '{field_name}' must be a non-empty string.")

    return value


# Read one required integer field from a dictionary.
def _require_int(payload: dict[str, Any], field_name: str, source_name: str) -> int:
    value = payload.get(field_name)
    if not isinstance(value, int):
        raise ValueError(f"{source_name} field '{field_name}' must be an integer.")

    return value


# Read one required object field from a dictionary.
def _require_dict(payload: dict[str, Any], field_name: str, source_name: str) -> dict[str, Any]:
    value = payload.get(field_name)
    if not isinstance(value, dict):
        raise ValueError(f"{source_name} field '{field_name}' must be an object.")

    return value


# Read a list of strings and convert it to an immutable tuple.
def _read_string_list(
    payload: dict[str, Any],
    field_name: str,
    source_name: str,
    required: bool = True,
) -> tuple[str, ...]:
    value = payload.get(field_name)
    if value is None and not required:
        return ()

    if not isinstance(value, list):
        raise ValueError(f"{source_name} field '{field_name}' must be a list.")

    normalized_items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{source_name} field '{field_name}' must contain non-empty strings.")

        normalized_items.append(item)

    return tuple(normalized_items)
