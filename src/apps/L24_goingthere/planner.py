# Deterministic two-stage movement planning for the L24 grid.

from __future__ import annotations

from src.apps.L24_goingthere.models import (
    GameState,
    MovementCommand,
    RockDirection,
)


LAST_COLUMN = 12
MIN_ROW = 1
MAX_ROW = 3


# Return the destination row after one movement command.
def destination_row(current_row: int, command: MovementCommand) -> int:
    if command is MovementCommand.LEFT:
        return current_row - 1
    if command is MovementCommand.RIGHT:
        return current_row + 1
    return current_row


# Return whether a command would leave the three-row grid.
def leaves_grid(state: GameState, command: MovementCommand) -> bool:
    target_row = destination_row(state.player_row, command)
    return not MIN_ROW <= target_row <= MAX_ROW


# Return whether the row-change stage crosses the current-column rock.
def crosses_current_stone(state: GameState, command: MovementCommand) -> bool:
    if command is MovementCommand.GO:
        return False
    return destination_row(state.player_row, command) == state.current_stone_row


# Return whether the next-column hint blocks one command destination.
def next_destination_is_blocked(
    state: GameState,
    command: MovementCommand,
    next_rock: RockDirection,
) -> bool:
    next_col = state.player_col + 1
    target_row = destination_row(state.player_row, command)
    if next_col == LAST_COLUMN and target_row == state.base_row:
        return False

    blocked_command = {
        RockDirection.LEFT: MovementCommand.LEFT,
        RockDirection.FRONT: MovementCommand.GO,
        RockDirection.RIGHT: MovementCommand.RIGHT,
    }[next_rock]
    return command is blocked_command


# Return all commands that pass grid, current-column, and next-column checks.
def safe_commands(
    state: GameState,
    next_rock: RockDirection,
) -> list[MovementCommand]:
    commands: list[MovementCommand] = []
    for command in MovementCommand:
        if leaves_grid(state, command):
            continue
        if crosses_current_stone(state, command):
            continue
        if next_destination_is_blocked(state, command, next_rock):
            continue
        commands.append(command)
    return commands


# Return whether one destination can still reach the base within remaining moves.
def base_remains_reachable(state: GameState, command: MovementCommand) -> bool:
    next_col = state.player_col + 1
    moves_remaining = LAST_COLUMN - next_col
    target_row = destination_row(state.player_row, command)
    return abs(state.base_row - target_row) <= moves_remaining


# Choose one deterministic safe command that preserves base reachability.
def choose_command(
    state: GameState,
    next_rock: RockDirection,
) -> MovementCommand:
    candidates = safe_commands(state, next_rock)
    if not candidates:
        raise ValueError(
            "No safe movement command remains after current and next-column checks."
        )

    reachable = [
        command for command in candidates if base_remains_reachable(state, command)
    ]
    if reachable:
        candidates = reachable

    priority = {
        MovementCommand.GO: 0,
        MovementCommand.LEFT: 1,
        MovementCommand.RIGHT: 2,
    }
    return min(
        candidates,
        key=lambda command: (
            abs(state.base_row - destination_row(state.player_row, command)),
            priority[command],
        ),
    )
