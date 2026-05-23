# Deterministic board solver for the L7 electricity puzzle.

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from src.apps.L7_electricity.L7_electricity_gpt_5_5.models import Board, Coordinate, Tile, all_coordinates
from src.apps.L7_electricity.L7_electricity_gpt_5_5.rotation import find_clockwise_turns_to_match, rotate_tile_clockwise


# Represents the required clockwise turns for one board coordinate.
@dataclass(frozen=True)
class TileRotationPlan:
    coordinate: Coordinate
    current_tile: Tile
    target_tile: Tile
    clockwise_turns: int

    # Return the hub coordinate label used in later API requests.
    @property
    def coordinate_label(self) -> str:
        return self.coordinate.label

    # Return the tile shape that should exist after applying the planned turns.
    @property
    def solved_tile(self) -> Tile:
        return rotate_tile_clockwise(self.current_tile, self.clockwise_turns)

    # Expand the tile plan into one label per required Hub rotation request.
    def to_rotation_sequence(self) -> list[str]:
        return [self.coordinate_label] * self.clockwise_turns


# Represents the full deterministic rotation plan for a 3x3 board.
@dataclass(frozen=True)
class BoardRotationPlan:
    current_board: Board
    target_board: Board
    tile_plans: tuple[TileRotationPlan, ...]

    # Return only the tile plans that require at least one real rotation.
    @property
    def changed_tile_plans(self) -> tuple[TileRotationPlan, ...]:
        return tuple(
            tile_plan
            for tile_plan in self.tile_plans
            if tile_plan.clockwise_turns > 0
        )

    # Return the total number of clockwise requests required by this plan.
    @property
    def total_rotations(self) -> int:
        return sum(tile_plan.clockwise_turns for tile_plan in self.tile_plans)

    # Return the ordered flat request sequence expected by the Hub.
    @property
    def rotation_sequence(self) -> list[str]:
        sequence: list[str] = []
        for tile_plan in self.changed_tile_plans:
            sequence.extend(tile_plan.to_rotation_sequence())
        return sequence

    # Return one JSON-friendly summary keyed by hub coordinate labels.
    def to_rotation_map(self) -> dict[str, int]:
        return {
            tile_plan.coordinate_label: tile_plan.clockwise_turns
            for tile_plan in self.tile_plans
        }


# Build one per-tile rotation plan for a single validated coordinate.
def build_tile_rotation_plan(
    coordinate: Coordinate,
    current_tile: Tile,
    target_tile: Tile,
) -> TileRotationPlan:
    turns = find_clockwise_turns_to_match(current_tile, target_tile)
    if turns is None:
        raise ValueError(
            "No rotation can match the target tile at "
            f"{coordinate.label}. Current: {current_tile.to_exit_names()}. "
            f"Target: {target_tile.to_exit_names()}."
        )

    return TileRotationPlan(
        coordinate=coordinate,
        current_tile=current_tile,
        target_tile=target_tile,
        clockwise_turns=turns,
    )


# Solve one full board pair into an ordered deterministic rotation plan.
def solve_board(current_board: Board, target_board: Board) -> BoardRotationPlan:
    tile_plans = tuple(
        build_tile_rotation_plan(
            coordinate=coordinate,
            current_tile=current_board.get_tile(coordinate),
            target_tile=target_board.get_tile(coordinate),
        )
        for coordinate in all_coordinates()
    )

    return BoardRotationPlan(
        current_board=current_board,
        target_board=target_board,
        tile_plans=tile_plans,
    )


# Build validated boards from raw label maps and solve them in one call.
def solve_label_maps(
    current_tile_map: Mapping[str, Iterable[str]],
    target_tile_map: Mapping[str, Iterable[str]],
) -> BoardRotationPlan:
    return solve_board(
        current_board=Board.from_label_map(current_tile_map),
        target_board=Board.from_label_map(target_tile_map),
    )
