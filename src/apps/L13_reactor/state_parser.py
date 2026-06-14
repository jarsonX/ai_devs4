# Strict parsing of Hub reactor payloads into validated state models.

from __future__ import annotations

from typing import Any

from src.apps.L13_reactor.models import Direction, ReactorBlock, ReactorState


# Read a required dictionary field with a useful contract error.
def _require_dict(payload: dict[str, Any], field: str) -> dict[str, Any]:
    value = payload.get(field)
    if not isinstance(value, dict):
        raise ValueError(f"Reactor response field {field!r} must be an object.")
    return value


# Read a required integer while rejecting booleans disguised as integers.
def _require_int(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Reactor response field {field!r} must be an integer.")
    return value


# Parse and validate the visual board returned by the Hub.
def _parse_board(value: Any) -> tuple[tuple[str, ...], ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("Reactor response field 'board' must be a non-empty list.")

    rows: list[tuple[str, ...]] = []
    expected_width: int | None = None
    for raw_row in value:
        if not isinstance(raw_row, list) or not all(
            isinstance(cell, str) for cell in raw_row
        ):
            raise ValueError("Every reactor board row must be a list of strings.")
        row = tuple(raw_row)
        if expected_width is None:
            expected_width = len(row)
        elif len(row) != expected_width:
            raise ValueError("Every reactor board row must have the same width.")
        rows.append(row)
    return tuple(rows)


# Parse one block and enforce the two-cell geometry contract.
def _parse_block(value: Any) -> ReactorBlock:
    if not isinstance(value, dict):
        raise ValueError("Every reactor block must be an object.")
    raw_direction = value.get("direction")
    try:
        direction = Direction(raw_direction)
    except ValueError as exc:
        raise ValueError(
            f"Unsupported reactor block direction: {raw_direction!r}."
        ) from exc
    return ReactorBlock(
        column=_require_int(value, "col"),
        top_row=_require_int(value, "top_row"),
        bottom_row=_require_int(value, "bottom_row"),
        direction=direction,
    )


# Convert one successful Hub payload into the internal reactor state.
def parse_reactor_state(payload: Any) -> ReactorState:
    if not isinstance(payload, dict):
        raise ValueError("Hub reactor response must be a JSON object.")

    player = _require_dict(payload, "player")
    goal = _require_dict(payload, "goal")
    raw_blocks = payload.get("blocks")
    if not isinstance(raw_blocks, list):
        raise ValueError("Reactor response field 'blocks' must be a list.")

    message = payload.get("message")
    if not isinstance(message, str):
        raise ValueError("Reactor response field 'message' must be a string.")
    reached_goal = payload.get("reached_goal")
    if not isinstance(reached_goal, bool):
        raise ValueError("Reactor response field 'reached_goal' must be a boolean.")

    state = ReactorState(
        code=_require_int(payload, "code"),
        message=message,
        board=_parse_board(payload.get("board")),
        player_column=_require_int(player, "col"),
        player_row=_require_int(player, "row"),
        goal_column=_require_int(goal, "col"),
        goal_row=_require_int(goal, "row"),
        blocks=tuple(_parse_block(block) for block in raw_blocks),
        reached_goal=reached_goal,
    )
    _validate_state_consistency(state)
    return state


# Check cross-field invariants that individual field validation cannot prove.
def _validate_state_consistency(state: ReactorState) -> None:
    board_height = len(state.board)
    board_width = len(state.board[0])
    for column, row, label in (
        (state.player_column, state.player_row, "player"),
        (state.goal_column, state.goal_row, "goal"),
    ):
        if not (1 <= column <= board_width and 1 <= row <= board_height):
            raise ValueError(f"Reactor {label} position is outside the board.")

    seen_columns: set[int] = set()
    for block in state.blocks:
        if block.column in seen_columns:
            raise ValueError("Reactor response contains duplicate block columns.")
        seen_columns.add(block.column)
        if not (1 <= block.column <= board_width):
            raise ValueError("Reactor block column is outside the board.")
        if not (1 <= block.top_row and block.bottom_row <= board_height):
            raise ValueError("Reactor block rows are outside the board.")

    if not state.reached_goal and state.is_occupied(
        state.player_column,
        state.player_row,
    ):
        raise ValueError("Hub returned a live player position occupied by a block.")
