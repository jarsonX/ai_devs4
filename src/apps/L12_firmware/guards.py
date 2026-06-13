# Deterministic command, filesystem, write, and submission guards.

from __future__ import annotations

import fnmatch
import posixpath
import re
import shlex
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Iterable

from src.apps.L12_firmware.repair_planner import (
    FIRMWARE_BINARY,
    FIRMWARE_DIRECTORY,
    LOCK_FILE,
    SETTINGS_FILE,
)

BASH_HISTORY_FILE = PurePosixPath("/home/operator/.bash_history")
FORBIDDEN_ROOTS = (
    PurePosixPath("/etc"),
    PurePosixPath("/root"),
    PurePosixPath("/proc"),
)
SIMPLE_COMMANDS = frozenset({"help", "pwd", "date", "uptime", "history", "whoami"})
BLOCKED_COMMANDS = frozenset({"find"})
DANGEROUS_COMMAND_CHARS = frozenset(";&|<>`$\\\r\n\x00*?[]#")
ECCS_PATTERN = re.compile(r"(?<![A-Za-z0-9])ECCS-[A-Za-z0-9]{40}(?![A-Za-z0-9])")
SAFE_LITERAL_PATTERN = re.compile(
    r"(?<![A-Za-z0-9._:@+-])"
    r"[A-Za-z0-9][A-Za-z0-9._:@+-]{0,127}"
    r"(?![A-Za-z0-9._:@+-])"
)


# Return one actionable allow-or-block decision for a proposed shell command.
@dataclass(frozen=True)
class CommandDecision:
    allowed: bool
    code: str
    message: str
    normalized_command: str | None = None
    resolved_path: str | None = None
    recovery_hint: str | None = None


# Return one actionable allow-or-block decision for a proposed Hub submission.
@dataclass(frozen=True)
class SubmissionDecision:
    allowed: bool
    code: str
    message: str
    confirmation: str | None = None


# Store one parsed .gitignore rule without requiring an extra dependency.
@dataclass(frozen=True)
class GitIgnoreRule:
    pattern: str
    negated: bool
    directory_only: bool
    anchored: bool


# Track only the VM state needed for deterministic safety checks.
@dataclass
class FirmwareGuardState:
    current_directory: PurePosixPath | None = None
    inspected_directories: set[PurePosixPath] = field(default_factory=set)
    pending_gitignore_directories: set[PurePosixPath] = field(default_factory=set)
    gitignore_rules: dict[PurePosixPath, tuple[GitIgnoreRule, ...]] = field(
        default_factory=dict
    )
    directory_entries: dict[PurePosixPath, tuple[str, ...]] = field(default_factory=dict)
    file_snapshots: dict[PurePosixPath, tuple[str, ...]] = field(default_factory=dict)
    projected_file_snapshots: dict[PurePosixPath, tuple[str, ...]] = field(
        default_factory=dict
    )
    observed_confirmation_codes: set[str] = field(default_factory=set)
    firmware_password_candidate_counts: dict[str, int] = field(default_factory=dict)

    # Reset observations after the remote VM is rebuilt.
    def reset(self) -> None:
        self.current_directory = None
        self.inspected_directories.clear()
        self.pending_gitignore_directories.clear()
        self.gitignore_rules.clear()
        self.directory_entries.clear()
        self.file_snapshots.clear()
        self.projected_file_snapshots.clear()
        self.observed_confirmation_codes.clear()
        self.firmware_password_candidate_counts.clear()

    # Record the canonical current directory reported by a successful pwd command.
    def record_current_directory(self, path: str) -> PurePosixPath:
        resolved_path = normalize_absolute_path(path)
        ensure_path_is_allowed(resolved_path)
        self.current_directory = resolved_path
        return resolved_path

    # Record one successful directory listing and whether .gitignore needs inspection.
    def record_directory_listing(
        self,
        directory: str | PurePosixPath,
        entries: Iterable[str],
    ) -> PurePosixPath:
        resolved_directory = self.resolve_path(str(directory))
        ensure_path_is_allowed(resolved_directory)
        self.inspected_directories.add(resolved_directory)
        entry_names = {
            PurePosixPath(entry.strip().rstrip("/")).name
            for entry in entries
            if entry.strip()
        }
        if ".gitignore" in entry_names:
            self.pending_gitignore_directories.add(resolved_directory)
        else:
            self.pending_gitignore_directories.discard(resolved_directory)
            self.gitignore_rules.setdefault(resolved_directory, ())
        self.directory_entries[resolved_directory] = tuple(sorted(entry_names))
        return resolved_directory

    # Record parsed .gitignore rules after the file was fetched successfully.
    def record_gitignore(
        self,
        directory: str | PurePosixPath,
        content: str,
    ) -> PurePosixPath:
        resolved_directory = self.resolve_path(str(directory))
        if resolved_directory not in self.inspected_directories:
            raise ValueError("Directory must be listed before recording .gitignore.")
        self.gitignore_rules[resolved_directory] = parse_gitignore(content)
        self.pending_gitignore_directories.discard(resolved_directory)
        return resolved_directory

    # Record one file read so later edits cannot target unseen or stale content.
    def record_file_snapshot(
        self,
        path: str | PurePosixPath,
        content: str,
    ) -> PurePosixPath:
        resolved_path = self.resolve_path(str(path))
        ensure_path_is_allowed(resolved_path)
        snapshot = tuple(content.splitlines())
        self.file_snapshots[resolved_path] = snapshot
        self.projected_file_snapshots[resolved_path] = snapshot
        return resolved_path

    # Invalidate the fresh snapshot, but keep a projected post-edit snapshot for planner state.
    def record_successful_edit(
        self,
        path: str | PurePosixPath,
        *,
        line_number: int,
        replacement_content: str,
    ) -> None:
        resolved_path = self.resolve_path(str(path))
        snapshot = self.file_snapshots.get(resolved_path)
        if snapshot is not None and 1 <= line_number <= len(snapshot):
            updated_snapshot = list(snapshot)
            updated_snapshot[line_number - 1] = replacement_content
            self.projected_file_snapshots[resolved_path] = tuple(updated_snapshot)
        self.file_snapshots.pop(resolved_path, None)

    # Remove one file from the last known directory listing after a successful delete.
    def record_removed_path(self, path: str | PurePosixPath) -> None:
        resolved_path = self.resolve_path(str(path))
        parent_entries = self.directory_entries.get(resolved_path.parent)
        if parent_entries is None:
            return
        self.directory_entries[resolved_path.parent] = tuple(
            entry
            for entry in parent_entries
            if entry != resolved_path.name
        )

    # Extract and remember confirmation codes from successful shell observations.
    def record_shell_observation(self, value: Any) -> set[str]:
        discovered_codes: set[str] = set()
        for text in iter_text_values(value):
            discovered_codes.update(ECCS_PATTERN.findall(text))
        self.observed_confirmation_codes.update(discovered_codes)
        return discovered_codes

    # Parse password candidates from exact firmware invocations in command history.
    def record_firmware_history(self, content: str) -> set[str]:
        candidate_counts: dict[str, int] = {}
        for raw_line in content.splitlines():
            try:
                arguments = shlex.split(raw_line.strip(), posix=True)
            except ValueError:
                continue
            if len(arguments) != 2 or arguments[0] != str(FIRMWARE_BINARY):
                continue
            candidate = arguments[1]
            if SAFE_LITERAL_PATTERN.fullmatch(candidate) is None:
                continue
            candidate_counts[candidate] = candidate_counts.get(candidate, 0) + 1
        self.firmware_password_candidate_counts = candidate_counts
        return {
            candidate
            for candidate, count in candidate_counts.items()
            if count >= 2
        }

    # Resolve one absolute or current-directory-relative Linux path.
    def resolve_path(self, path: str) -> PurePosixPath:
        cleaned_path = path.strip()
        if not cleaned_path:
            if self.current_directory is None:
                raise ValueError("Current directory is unknown; run pwd first.")
            return self.current_directory
        if cleaned_path.startswith("/"):
            return normalize_absolute_path(cleaned_path)
        if self.current_directory is None:
            raise ValueError("Relative paths require a successful pwd first.")
        return normalize_absolute_path(f"{self.current_directory}/{cleaned_path}")

    # Check whether known .gitignore rules exclude one resolved path.
    def is_ignored(self, path: PurePosixPath) -> bool:
        ignored = False
        for base_directory in sorted(
            self.gitignore_rules,
            key=lambda item: len(item.parts),
        ):
            if path == base_directory or base_directory not in path.parents:
                continue
            relative_path = path.relative_to(base_directory)
            for rule in self.gitignore_rules[base_directory]:
                if gitignore_rule_matches(rule, relative_path):
                    ignored = not rule.negated
        return ignored


# Normalize a Linux path without touching the local filesystem.
def normalize_absolute_path(path: str) -> PurePosixPath:
    normalized = posixpath.normpath(path.strip())
    if not normalized.startswith("/"):
        raise ValueError("Expected an absolute Linux path.")
    return PurePosixPath(normalized)


# Block paths inside the task's explicitly forbidden system directories.
def ensure_path_is_allowed(path: PurePosixPath) -> None:
    for forbidden_root in FORBIDDEN_ROOTS:
        if path == forbidden_root or forbidden_root in path.parents:
            raise ValueError(f"Path is forbidden: {forbidden_root}.")


# Return ancestors from root through the requested directory.
def iter_directory_chain(directory: PurePosixPath) -> list[PurePosixPath]:
    if directory == PurePosixPath("/"):
        return [directory]
    chain = [PurePosixPath("/")]
    current = PurePosixPath("/")
    for part in directory.parts[1:]:
        current = current / part
        chain.append(current)
    return chain


# Parse the subset of gitignore syntax needed for safe path exclusion.
def parse_gitignore(content: str) -> tuple[GitIgnoreRule, ...]:
    rules: list[GitIgnoreRule] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        negated = line.startswith("!")
        if negated:
            line = line[1:].strip()
        if not line:
            continue
        directory_only = line.endswith("/")
        line = line.rstrip("/")
        anchored = line.startswith("/")
        line = line.lstrip("/")
        if line:
            rules.append(
                GitIgnoreRule(
                    pattern=line,
                    negated=negated,
                    directory_only=directory_only,
                    anchored=anchored,
                )
            )
    return tuple(rules)


# Match one parsed .gitignore rule against a path relative to its directory.
def gitignore_rule_matches(
    rule: GitIgnoreRule,
    relative_path: PurePosixPath,
) -> bool:
    relative_text = relative_path.as_posix()
    if relative_text == ".":
        return False

    if rule.anchored or "/" in rule.pattern:
        matched = fnmatch.fnmatchcase(relative_text, rule.pattern)
        if rule.directory_only:
            return (
                relative_text == rule.pattern
                or relative_text.startswith(f"{rule.pattern}/")
                or matched
            )
        return matched

    for part_index, part in enumerate(relative_path.parts):
        if fnmatch.fnmatchcase(part, rule.pattern):
            if not rule.directory_only:
                return True
            return part_index < len(relative_path.parts)
    return False


# Yield all string values from nested shell response data.
def iter_text_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested_value in value.values():
            yield from iter_text_values(nested_value)
    elif isinstance(value, (list, tuple)):
        for nested_value in value:
            yield from iter_text_values(nested_value)


# Return a blocked command decision with a stable recovery shape.
def blocked_command(
    code: str,
    message: str,
    recovery_hint: str,
) -> CommandDecision:
    return CommandDecision(
        allowed=False,
        code=code,
        message=message,
        recovery_hint=recovery_hint,
    )


# Enforce directory-listing and .gitignore checks before path access.
def validate_path_access(
    state: FirmwareGuardState,
    path: PurePosixPath,
    *,
    operation: str,
) -> CommandDecision | None:
    try:
        ensure_path_is_allowed(path)
    except ValueError as error:
        return blocked_command(
            "forbidden_path",
            str(error),
            "Choose a path outside /etc, /root, and /proc.",
        )

    if state.is_ignored(path):
        return blocked_command(
            "gitignored_path",
            f"Path is excluded by a discovered .gitignore: {path}.",
            "Do not access this path.",
        )

    target_directory = path if operation in {"list", "change_directory"} else path.parent
    chain = iter_directory_chain(target_directory)
    directories_to_check = chain[:-1] if operation in {"list", "change_directory"} else chain

    for directory in directories_to_check:
        if directory not in state.inspected_directories:
            return blocked_command(
                "directory_not_inspected",
                f"Directory must be listed before accessing descendants: {directory}.",
                f"Run ls {directory} and inspect any .gitignore first.",
            )
        if directory in state.pending_gitignore_directories:
            return blocked_command(
                "gitignore_not_loaded",
                f"Directory contains an unread .gitignore: {directory}.",
                f"Run cat {directory}/.gitignore before continuing.",
            )
    return None


# Validate one proposed shell command against the bounded firmware policy.
def validate_shell_command(
    command: str,
    state: FirmwareGuardState,
    *,
    max_command_chars: int,
) -> CommandDecision:
    cleaned_command = command.strip()
    if not cleaned_command:
        return blocked_command(
            "empty_command",
            "Command must not be empty.",
            "Choose one supported shell command.",
        )
    if len(cleaned_command) > max_command_chars:
        return blocked_command(
            "command_too_long",
            f"Command exceeds the {max_command_chars}-character limit.",
            "Use one short command.",
        )
    if any(character in cleaned_command for character in DANGEROUS_COMMAND_CHARS):
        return blocked_command(
            "shell_metacharacter",
            "Command contains blocked shell or wildcard metacharacters.",
            "Use one literal command without chaining, redirects, substitutions, or wildcards.",
        )

    try:
        arguments = shlex.split(cleaned_command, posix=True)
    except ValueError as error:
        return blocked_command(
            "invalid_command_syntax",
            str(error),
            "Fix the command quoting and try again.",
        )
    if not arguments:
        return blocked_command(
            "empty_command",
            "Command must not be empty.",
            "Choose one supported shell command.",
        )

    command_name = arguments[0]
    if command_name in BLOCKED_COMMANDS:
        return blocked_command(
            "blocked_command",
            f"Command is forbidden for this task: {command_name}.",
            "Use targeted ls, cat, cd, or the approved firmware executable.",
        )
    if command_name == "rm":
        if len(arguments) != 2:
            return blocked_command(
                "explicit_path_required",
                "rm requires exactly one literal path.",
                f"Run only: rm {LOCK_FILE}",
            )
        try:
            resolved_path = state.resolve_path(arguments[1])
        except ValueError as error:
            return blocked_command(
                "path_resolution_failed",
                str(error),
                f"Use the absolute lock-file path: {LOCK_FILE}",
            )
        if resolved_path != LOCK_FILE:
            return blocked_command(
                "delete_target_blocked",
                f"Deletion is allowed only for {LOCK_FILE}.",
                f"Remove only the observed lock file: rm {LOCK_FILE}",
            )
        path_decision = validate_path_access(state, resolved_path, operation="delete")
        if path_decision:
            return path_decision
        cooler_entries = state.directory_entries.get(FIRMWARE_DIRECTORY, ())
        if LOCK_FILE.name not in cooler_entries:
            return blocked_command(
                "lock_file_not_observed",
                "The firmware lock file was not present in the latest cooler directory listing.",
                f"Run ls {FIRMWARE_DIRECTORY} before trying to remove the lock file.",
            )
        return CommandDecision(
            True,
            "allowed_lock_delete",
            "Observed firmware lock-file removal is allowed.",
            f"rm {LOCK_FILE}",
            str(LOCK_FILE),
        )
    if command_name in SIMPLE_COMMANDS:
        if len(arguments) != 1:
            return blocked_command(
                "unexpected_arguments",
                f"{command_name} does not accept arguments.",
                f"Run only: {command_name}",
            )
        return CommandDecision(True, "allowed", "Command is allowed.", cleaned_command)
    if command_name == "reboot":
        if len(arguments) != 1:
            return blocked_command(
                "unexpected_arguments",
                "reboot does not accept arguments.",
                "Run only: reboot",
            )
        return CommandDecision(True, "allowed_reboot", "VM reset is allowed.", "reboot")
    if command_name == str(FIRMWARE_BINARY):
        if len(arguments) < 2:
            return blocked_command(
                "binary_argument_required",
                "The approved firmware binary requires exactly one grounded password argument.",
                f"Run {FIRMWARE_BINARY} with one observed password argument.",
            )
        if len(arguments) > 2:
            return blocked_command(
                "binary_arguments_blocked",
                "The approved firmware binary accepts exactly one grounded password argument.",
                f"Run {FIRMWARE_BINARY} with one observed password argument.",
            )
        path_decision = validate_path_access(
            state,
            FIRMWARE_BINARY,
            operation="execute",
        )
        if path_decision:
            return path_decision
        password = arguments[1]
        if SAFE_LITERAL_PATTERN.fullmatch(password) is None:
            return blocked_command(
                "unsafe_binary_argument",
                "The firmware password contains unsupported characters or length.",
                "Use one short literal containing only letters, digits, dot, underscore, colon, at, plus, or hyphen.",
            )
        if state.firmware_password_candidate_counts.get(password, 0) < 2:
            return blocked_command(
                "binary_argument_not_grounded",
                "The firmware password argument lacks repeated command-history evidence.",
                "Read allowed command history and use a value that appears at least twice as the sole cooler.bin argument.",
            )
        normalized_command = f"{FIRMWARE_BINARY} {password}"
        return CommandDecision(
            True,
            "allowed_execution",
            "Approved firmware executable is allowed.",
            normalized_command,
            str(FIRMWARE_BINARY),
        )
    if command_name == "ls":
        if len(arguments) > 2:
            return blocked_command(
                "unexpected_arguments",
                "ls accepts at most one path.",
                "Run ls with zero or one literal path.",
            )
        try:
            resolved_path = state.resolve_path(arguments[1] if len(arguments) == 2 else "")
        except ValueError as error:
            return blocked_command(
                "path_resolution_failed",
                str(error),
                "Run pwd first or provide an absolute path.",
            )
        path_decision = validate_path_access(state, resolved_path, operation="list")
        if path_decision:
            return path_decision
        return CommandDecision(
            True,
            "allowed_list",
            "Directory listing is allowed.",
            f"ls {resolved_path}",
            str(resolved_path),
        )
    if command_name == "cd":
        if len(arguments) != 2:
            return blocked_command(
                "explicit_path_required",
                "cd requires one explicit path so state remains traceable.",
                "Run cd with one literal path.",
            )
        try:
            resolved_path = state.resolve_path(arguments[1])
        except ValueError as error:
            return blocked_command(
                "path_resolution_failed",
                str(error),
                "Run pwd first or provide an absolute path.",
            )
        path_decision = validate_path_access(
            state,
            resolved_path,
            operation="change_directory",
        )
        if path_decision:
            return path_decision
        return CommandDecision(
            True,
            "allowed_cd",
            "Directory change is allowed.",
            f"cd {resolved_path}",
            str(resolved_path),
        )
    if command_name == "cat":
        if len(arguments) != 2:
            return blocked_command(
                "explicit_path_required",
                "cat requires exactly one literal path.",
                "Run cat with one file or directory path.",
            )
        try:
            resolved_path = state.resolve_path(arguments[1])
        except ValueError as error:
            return blocked_command(
                "path_resolution_failed",
                str(error),
                "Run pwd first or provide an absolute path.",
            )
        is_pending_gitignore = (
            resolved_path.name == ".gitignore"
            and resolved_path.parent in state.pending_gitignore_directories
        )
        if not is_pending_gitignore:
            path_decision = validate_path_access(state, resolved_path, operation="read")
            if path_decision:
                return path_decision
        else:
            ancestor_decision = validate_path_access(
                state,
                resolved_path.parent,
                operation="change_directory",
            )
            if ancestor_decision:
                return ancestor_decision
        return CommandDecision(
            True,
            "allowed_read",
            "Path read is allowed.",
            f"cat {resolved_path}",
            str(resolved_path),
        )
    if command_name == "editline":
        if len(arguments) < 4:
            return blocked_command(
                "edit_arguments_missing",
                "editline requires a file, line number, and replacement content.",
                f"Use: editline {SETTINGS_FILE} <line-number> <content>",
            )
        try:
            resolved_path = state.resolve_path(arguments[1])
        except ValueError as error:
            return blocked_command(
                "path_resolution_failed",
                str(error),
                "Use the absolute settings.ini path.",
            )
        if resolved_path != SETTINGS_FILE:
            return blocked_command(
                "write_target_blocked",
                f"Writes are allowed only to {SETTINGS_FILE}.",
                f"Read and edit only {SETTINGS_FILE}.",
            )
        path_decision = validate_path_access(state, resolved_path, operation="write")
        if path_decision:
            return path_decision
        try:
            line_number = int(arguments[2])
        except ValueError:
            return blocked_command(
                "invalid_line_number",
                "editline line number must be an integer.",
                "Use a positive line number from the latest settings.ini read.",
            )
        snapshot = state.file_snapshots.get(SETTINGS_FILE)
        if snapshot is None:
            return blocked_command(
                "settings_snapshot_required",
                "settings.ini must be read after the latest edit or reboot.",
                f"Run cat {SETTINGS_FILE} before editing.",
            )
        if line_number < 1 or line_number > len(snapshot):
            return blocked_command(
                "line_out_of_range",
                f"Line {line_number} is outside the current settings.ini snapshot.",
                f"Choose a line from 1 to {len(snapshot)}.",
            )
        replacement_content = " ".join(arguments[3:]).strip()
        if not replacement_content:
            return blocked_command(
                "empty_replacement",
                "Replacement content must not be empty.",
                "Provide the complete replacement line.",
            )
        normalized_command = (
            f"editline {SETTINGS_FILE} {line_number} {replacement_content}"
        )
        return CommandDecision(
            True,
            "allowed_edit",
            "Bounded settings.ini edit is allowed.",
            normalized_command,
            str(SETTINGS_FILE),
        )

    return blocked_command(
        "unsupported_command",
        f"Command is not exposed by the bounded firmware policy: {command_name}.",
        "Use help, pwd, ls, cat, cd, editline, reboot, date, uptime, history, whoami, the approved firmware executable, or rm for the exact lock file.",
    )


# Allow submission only for an exact confirmation code observed in shell output.
def validate_confirmation_submission(
    confirmation: str,
    state: FirmwareGuardState,
) -> SubmissionDecision:
    cleaned_confirmation = confirmation.strip()
    if ECCS_PATTERN.fullmatch(cleaned_confirmation) is None:
        return SubmissionDecision(
            allowed=False,
            code="invalid_confirmation_format",
            message="Confirmation must match ECCS- followed by 40 alphanumeric characters.",
        )
    if cleaned_confirmation not in state.observed_confirmation_codes:
        return SubmissionDecision(
            allowed=False,
            code="confirmation_not_observed",
            message="Confirmation was not observed in a shell API response.",
        )
    return SubmissionDecision(
        allowed=True,
        code="allowed_submission",
        message="Observed confirmation code is eligible for submission.",
        confirmation=cleaned_confirmation,
    )
