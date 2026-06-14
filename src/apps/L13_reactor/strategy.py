# Deterministic hazard prediction and command selection for the reactor board.

from __future__ import annotations

from src.apps.L13_reactor.models import Direction, ReactorBlock, ReactorState


# Predict one block after the next command and flip direction at board extremes.
def predict_block(block: ReactorBlock, *, board_height: int) -> ReactorBlock:
    lowest_top_row = board_height - 1
    if block.direction is Direction.DOWN:
        next_top_row = block.top_row + 1
        next_direction = (
            Direction.UP if next_top_row >= lowest_top_row else Direction.DOWN
        )
    else:
        next_top_row = block.top_row - 1
        next_direction = Direction.DOWN if next_top_row <= 1 else Direction.UP

    if not (1 <= next_top_row <= lowest_top_row):
        raise ValueError("Block direction is inconsistent with its boundary position.")
    return ReactorBlock(
        column=block.column,
        top_row=next_top_row,
        bottom_row=next_top_row + 1,
        direction=next_direction,
    )


# Predict every block position after one robot command.
def predict_blocks(state: ReactorState) -> tuple[ReactorBlock, ...]:
    return tuple(
        predict_block(block, board_height=len(state.board))
        for block in state.blocks
    )


# Report whether predicted blocks occupy one board cell.
def _is_occupied(
    blocks: tuple[ReactorBlock, ...],
    column: int,
    row: int,
) -> bool:
    return any(block.occupies(column, row) for block in blocks)


# Require a horizontal destination to stay clear across the full transition.
def _horizontal_move_is_safe(
    state: ReactorState,
    predicted_blocks: tuple[ReactorBlock, ...],
    destination_column: int,
) -> bool:
    if not (1 <= destination_column <= len(state.board[0])):
        return False
    return not state.is_occupied(
        destination_column,
        state.player_row,
    ) and not _is_occupied(
        predicted_blocks,
        destination_column,
        state.player_row,
    )


# Choose progress first, then waiting, then a safe retreat.
def choose_command(state: ReactorState) -> str:
    if state.reached_goal:
        raise ValueError("No command is needed after reaching the reactor goal.")

    predicted_blocks = predict_blocks(state)
    right_column = state.player_column + 1
    if _horizontal_move_is_safe(state, predicted_blocks, right_column):
        return "right"

    if not _is_occupied(
        predicted_blocks,
        state.player_column,
        state.player_row,
    ):
        return "wait"

    left_column = state.player_column - 1
    if _horizontal_move_is_safe(state, predicted_blocks, left_column):
        return "left"

    raise RuntimeError(
        "No safe reactor command exists for the predicted next transition."
    )
