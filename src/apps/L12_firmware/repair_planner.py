# Deterministic repair planning for the firmware configuration workflow.

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath


SETTINGS_FILE = PurePosixPath("/opt/firmware/cooler/settings.ini")
LOCK_FILE = PurePosixPath("/opt/firmware/cooler/cooler-is-blocked.lock")
FIRMWARE_DIRECTORY = PurePosixPath("/opt/firmware/cooler")
FIRMWARE_BINARY = PurePosixPath("/opt/firmware/cooler/cooler.bin")

SECTION_PATTERN = re.compile(r"^\s*\[([^\]]+)\]\s*$")
COMMENTED_SETTING_PATTERN = re.compile(r"^\s*#\s*([A-Za-z0-9_]+)\s*=(.*)$")
SETTING_PATTERN = re.compile(r"^\s*([A-Za-z0-9_]+)\s*=(.*)$")


# Describe one settings line the planner can reason about.
@dataclass(frozen=True)
class ParsedSetting:
    line_number: int
    section: str | None
    key: str
    value: str
    commented: bool


# Describe one exact edit the planner wants the model to apply.
@dataclass(frozen=True)
class PlannedEdit:
    line_number: int
    replacement: str
    reason: str

    # Convert one planned edit into a JSON-ready structure for tool context.
    def to_dict(self) -> dict[str, object]:
        return {
            "line_number": self.line_number,
            "replacement": self.replacement,
            "reason": self.reason,
        }


# Describe the bounded planner state the model should follow.
@dataclass(frozen=True)
class RepairPlan:
    phase: str
    summary: str
    edits: tuple[PlannedEdit, ...]
    chosen_password: str | None = None
    lock_file_present: bool = False
    lock_file_removal_command: str | None = None
    binary_command: str | None = None
    missing_inputs: tuple[str, ...] = ()

    # Convert the plan into a compact JSON-ready payload for the model.
    def to_dict(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "summary": self.summary,
            "edits": [edit.to_dict() for edit in self.edits],
            "chosen_password": self.chosen_password,
            "lock_file_present": self.lock_file_present,
            "lock_file_removal_command": self.lock_file_removal_command,
            "binary_command": self.binary_command,
            "missing_inputs": list(self.missing_inputs),
        }


# Parse one settings snapshot into section-aware key/value records.
def parse_settings_snapshot(lines: tuple[str, ...]) -> tuple[ParsedSetting, ...]:
    section: str | None = None
    parsed_settings: list[ParsedSetting] = []
    for index, raw_line in enumerate(lines, start=1):
        section_match = SECTION_PATTERN.match(raw_line)
        if section_match:
            section = section_match.group(1)
            continue

        commented_match = COMMENTED_SETTING_PATTERN.match(raw_line)
        if commented_match:
            parsed_settings.append(
                ParsedSetting(
                    line_number=index,
                    section=section,
                    key=commented_match.group(1),
                    value=commented_match.group(2).strip(),
                    commented=True,
                )
            )
            continue

        setting_match = SETTING_PATTERN.match(raw_line)
        if setting_match:
            parsed_settings.append(
                ParsedSetting(
                    line_number=index,
                    section=section,
                    key=setting_match.group(1),
                    value=setting_match.group(2).strip(),
                    commented=False,
                )
            )
    return tuple(parsed_settings)


# Choose one password only when there is a unique strongest repeated candidate.
def choose_grounded_password(
    candidate_counts: dict[str, int],
) -> str | None:
    grounded_candidates = [
        (candidate, count)
        for candidate, count in candidate_counts.items()
        if count >= 2
    ]
    if not grounded_candidates:
        return None
    grounded_candidates.sort(key=lambda item: (-item[1], item[0]))
    strongest_candidate, strongest_count = grounded_candidates[0]
    tied_candidates = [
        candidate
        for candidate, count in grounded_candidates
        if count == strongest_count
    ]
    if len(tied_candidates) > 1:
        return None
    return strongest_candidate


# Build one deterministic plan from observed settings, password history, and directory state.
def build_repair_plan(
    *,
    settings_snapshot: tuple[str, ...] | None,
    settings_snapshot_fresh: bool,
    firmware_directory_entries: tuple[str, ...] | None,
    password_candidate_counts: dict[str, int],
) -> RepairPlan:
    chosen_password = choose_grounded_password(password_candidate_counts)
    lock_file_present = (
        firmware_directory_entries is not None
        and LOCK_FILE.name in firmware_directory_entries
    )
    lock_file_removal_command = (
        f"rm {LOCK_FILE}" if lock_file_present else None
    )
    binary_command = (
        f"{FIRMWARE_BINARY} {chosen_password}"
        if chosen_password is not None and not lock_file_present
        else None
    )

    missing_inputs: list[str] = []
    if lock_file_present:
        return RepairPlan(
            phase="remove_lock",
            summary="Remove the observed lock file before attempting repairs or execution.",
            edits=(),
            chosen_password=chosen_password,
            lock_file_present=True,
            lock_file_removal_command=lock_file_removal_command,
            binary_command=None,
        )

    if firmware_directory_entries is None:
        missing_inputs.append(f"ls {FIRMWARE_DIRECTORY}")
    if chosen_password is None:
        missing_inputs.append("cat /home/operator/.bash_history")
    if settings_snapshot is None:
        missing_inputs.append(f"cat {SETTINGS_FILE}")
    if missing_inputs:
        return RepairPlan(
            phase="inspect_inputs",
            summary="Planner is waiting for settings, firmware directory state, or grounded password evidence.",
            edits=(),
            chosen_password=chosen_password,
            lock_file_present=lock_file_present,
            lock_file_removal_command=lock_file_removal_command,
            binary_command=binary_command,
            missing_inputs=tuple(missing_inputs),
        )

    parsed_settings = parse_settings_snapshot(settings_snapshot)
    edits: list[PlannedEdit] = []
    for section, key, target_value, allow_uncomment, reason in (
        ("main", "SAFETY_CHECK", "pass", True, "Enable the main safety check."),
        ("test_mode", "enabled", "false", False, "Disable test mode."),
        ("cooling", "enabled", "true", False, "Enable cooling."),
    ):
        edit = plan_setting_edit(
            parsed_settings,
            section=section,
            key=key,
            target_value=target_value,
            allow_uncomment=allow_uncomment,
            reason=reason,
        )
        if edit is not None:
            edits.append(edit)

    if edits and not settings_snapshot_fresh:
        return RepairPlan(
            phase="inspect_inputs",
            summary="Planner knows more settings repairs are needed, but a fresh settings.ini reread is required before another edit.",
            edits=(),
            chosen_password=chosen_password,
            lock_file_present=False,
            binary_command=None,
            missing_inputs=(f"cat {SETTINGS_FILE}",),
        )

    if edits:
        return RepairPlan(
            phase="apply_repairs",
            summary="Apply the deterministic firmware configuration edits before executing the binary.",
            edits=tuple(edits),
            chosen_password=chosen_password,
            lock_file_present=False,
            binary_command=None,
        )

    return RepairPlan(
        phase="execute_binary",
        summary="Configuration already matches the deterministic target. Execute the firmware once with the grounded password.",
        edits=(),
        chosen_password=chosen_password,
        lock_file_present=False,
        binary_command=binary_command,
    )


# Plan one section-aware line replacement if the current value differs from target.
def plan_setting_edit(
    parsed_settings: tuple[ParsedSetting, ...],
    *,
    section: str,
    key: str,
    target_value: str,
    allow_uncomment: bool,
    reason: str,
) -> PlannedEdit | None:
    for setting in parsed_settings:
        if setting.section != section or setting.key != key:
            continue
        if (
            setting.value == target_value
            and (not setting.commented or allow_uncomment is False)
        ):
            return None
        replacement = f"{key}={target_value}"
        if setting.commented and not allow_uncomment:
            replacement = f"{key}={target_value}"
        return PlannedEdit(
            line_number=setting.line_number,
            replacement=replacement,
            reason=reason,
        )
    return None
