# Deterministic rotation helpers for directions and tile shapes.

from __future__ import annotations

from src.apps.L7_electricity.L7_electricity_gpt_5_5.models import Direction, Tile


DIRECTION_ORDER = (
    Direction.UP,
    Direction.RIGHT,
    Direction.DOWN,
    Direction.LEFT,
)


# Normalize any integer turn count to the equivalent 0-3 clockwise range.
def normalize_clockwise_turns(turns: int) -> int:
    return turns % len(DIRECTION_ORDER)


# Rotate one direction clockwise by the requested number of 90-degree turns.
def rotate_direction_clockwise(direction: Direction, turns: int = 1) -> Direction:
    normalized_turns = normalize_clockwise_turns(turns)
    start_index = DIRECTION_ORDER.index(direction)
    rotated_index = (start_index + normalized_turns) % len(DIRECTION_ORDER)
    return DIRECTION_ORDER[rotated_index]


# Rotate one tile clockwise by the requested number of 90-degree turns.
def rotate_tile_clockwise(tile: Tile, turns: int = 1) -> Tile:
    rotated_exits = {
        rotate_direction_clockwise(direction, turns)
        for direction in tile.exits
    }
    return Tile(exits=frozenset(rotated_exits))


# Return every unique clockwise orientation reachable within one full cycle.
def generate_tile_rotations(tile: Tile) -> tuple[Tile, ...]:
    rotations: list[Tile] = []
    seen_tiles: set[Tile] = set()

    for turns in range(len(DIRECTION_ORDER)):
        rotated_tile = rotate_tile_clockwise(tile, turns)
        if rotated_tile in seen_tiles:
            continue

        rotations.append(rotated_tile)
        seen_tiles.add(rotated_tile)

    return tuple(rotations)


# Check whether one tile matches another after the requested clockwise turns.
def tile_matches_after_rotation(source: Tile, target: Tile, turns: int) -> bool:
    return rotate_tile_clockwise(source, turns) == target


# Return the minimal clockwise turns needed to match the target tile shape.
def find_clockwise_turns_to_match(source: Tile, target: Tile) -> int | None:
    if source.exit_count != target.exit_count:
        return None

    for turns in range(len(DIRECTION_ORDER)):
        if tile_matches_after_rotation(source, target, turns):
            return turns

    return None
