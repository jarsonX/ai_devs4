# Core domain models for the L7 electricity puzzle workflow.

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Iterable, Mapping


BOARD_SIZE = 3
ALLOWED_EXIT_COUNTS = frozenset({2, 3})


# Represents one allowed cable direction on a tile edge.
class Direction(str, Enum):
    UP = "up"
    RIGHT = "right"
    DOWN = "down"
    LEFT = "left"


# Represents one validated board coordinate in 1-based hub format.
@dataclass(frozen=True)
class Coordinate:
    row: int
    column: int

    # Validate that the coordinate stays inside the fixed 3x3 board.
    def __post_init__(self) -> None:
        if not 1 <= self.row <= BOARD_SIZE:
            raise ValueError(f"row must be between 1 and {BOARD_SIZE}.")
        if not 1 <= self.column <= BOARD_SIZE:
            raise ValueError(f"column must be between 1 and {BOARD_SIZE}.")

    # Return the hub coordinate label used in requests and parsed maps.
    @property
    def label(self) -> str:
        return f"{self.row}x{self.column}"

    # Build one coordinate from a hub-style label such as 2x3.
    @classmethod
    def from_label(cls, label: str) -> Coordinate:
        normalized_label = label.strip().lower()
        parts = normalized_label.split("x")
        if len(parts) != 2:
            raise ValueError(f"Invalid coordinate label: {label!r}.")

        try:
            row = int(parts[0])
            column = int(parts[1])
        except ValueError as error:
            raise ValueError(f"Invalid coordinate label: {label!r}.") from error

        return cls(row=row, column=column)


# Represents one validated tile shape as a set of cable exits.
@dataclass(frozen=True)
class Tile:
    exits: frozenset[Direction]

    # Validate the allowed tile shape and normalize exit storage.
    def __post_init__(self) -> None:
        normalized_exits = frozenset(self.exits)
        if len(normalized_exits) not in ALLOWED_EXIT_COUNTS:
            raise ValueError(
                "Tile must have exactly 2 or 3 unique exits."
            )

        object.__setattr__(self, "exits", normalized_exits)

    # Build one tile from raw direction names such as ["up", "right"].
    @classmethod
    def from_exit_names(cls, exit_names: Iterable[str]) -> Tile:
        normalized_names = [name.strip().lower() for name in exit_names]
        try:
            exits = frozenset(Direction(name) for name in normalized_names)
        except ValueError as error:
            raise ValueError(
                f"Unknown tile exit in {normalized_names!r}."
            ) from error

        return cls(exits=exits)

    # Return the number of cable exits in this tile shape.
    @property
    def exit_count(self) -> int:
        return len(self.exits)

    # Return exit names in a stable order for storage and comparison output.
    def to_exit_names(self) -> list[str]:
        ordered_directions = (Direction.UP, Direction.RIGHT, Direction.DOWN, Direction.LEFT)
        return [direction.value for direction in ordered_directions if direction in self.exits]


# Represents one fully validated 3x3 board state.
@dataclass(frozen=True)
class Board:
    tiles: Mapping[Coordinate, Tile]

    # Validate that the board contains exactly one tile for every coordinate.
    def __post_init__(self) -> None:
        normalized_tiles = dict(self.tiles)
        expected_coordinates = {Coordinate(row, column) for row in range(1, BOARD_SIZE + 1) for column in range(1, BOARD_SIZE + 1)}
        actual_coordinates = set(normalized_tiles)

        missing_coordinates = expected_coordinates - actual_coordinates
        extra_coordinates = actual_coordinates - expected_coordinates
        if missing_coordinates or extra_coordinates:
            missing_labels = sorted(coordinate.label for coordinate in missing_coordinates)
            extra_labels = sorted(coordinate.label for coordinate in extra_coordinates)
            raise ValueError(
                "Board must contain exactly the 3x3 coordinate set. "
                f"Missing: {missing_labels}. Extra: {extra_labels}."
            )

        object.__setattr__(self, "tiles", MappingProxyType(normalized_tiles))

    # Build one board from a parsed hub-style mapping keyed by coordinate labels.
    @classmethod
    def from_label_map(cls, tile_map: Mapping[str, Iterable[str]]) -> Board:
        normalized_tiles = {
            Coordinate.from_label(label): Tile.from_exit_names(exit_names)
            for label, exit_names in tile_map.items()
        }
        return cls(tiles=normalized_tiles)

    # Return one tile by validated coordinate object.
    def get_tile(self, coordinate: Coordinate) -> Tile:
        return self.tiles[coordinate]

    # Return one tile by hub-style coordinate label.
    def get_tile_by_label(self, label: str) -> Tile:
        return self.get_tile(Coordinate.from_label(label))

    # Convert the board back into a stable label-keyed mapping of exit names.
    def to_label_map(self) -> dict[str, list[str]]:
        return {
            coordinate.label: self.tiles[coordinate].to_exit_names()
            for coordinate in all_coordinates()
        }


# Return all valid coordinates in row-major order for board operations.
def all_coordinates() -> tuple[Coordinate, ...]:
    return tuple(
        Coordinate(row=row, column=column)
        for row in range(1, BOARD_SIZE + 1)
        for column in range(1, BOARD_SIZE + 1)
    )
