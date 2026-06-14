# Validated state models for the deterministic reactor controller.

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# Represent the only two vertical block movement directions.
class Direction(str, Enum):
    UP = "up"
    DOWN = "down"


# Represent one two-cell reactor block in a fixed column.
@dataclass(frozen=True)
class ReactorBlock:
    column: int
    top_row: int
    bottom_row: int
    direction: Direction

    # Reject malformed block geometry before strategy calculations use it.
    def __post_init__(self) -> None:
        if self.bottom_row != self.top_row + 1:
            raise ValueError("A reactor block must occupy exactly two adjacent rows.")

    # Report whether this block currently occupies one board cell.
    def occupies(self, column: int, row: int) -> bool:
        return self.column == column and self.top_row <= row <= self.bottom_row


# Represent one complete state snapshot returned after a command.
@dataclass(frozen=True)
class ReactorState:
    code: int
    message: str
    board: tuple[tuple[str, ...], ...]
    player_column: int
    player_row: int
    goal_column: int
    goal_row: int
    blocks: tuple[ReactorBlock, ...]
    reached_goal: bool

    # Report whether any current block occupies one board cell.
    def is_occupied(self, column: int, row: int) -> bool:
        return any(block.occupies(column, row) for block in self.blocks)


# Summarize one completed or interrupted bounded reactor run.
@dataclass(frozen=True)
class WorkflowResult:
    completed: bool
    commands_sent: int
    final_player_column: int | None
    final_player_row: int | None
    final_message: str
    log_path: str
    flag_found: bool
