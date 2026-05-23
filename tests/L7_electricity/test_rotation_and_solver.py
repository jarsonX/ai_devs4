# Unit tests for L7 electricity tile rotation and board solving.

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.apps.L7_electricity.models import Board, Direction, Tile
from src.apps.L7_electricity.rotation import (
    find_clockwise_turns_to_match,
    generate_tile_rotations,
    rotate_direction_clockwise,
    rotate_tile_clockwise,
)
from src.apps.L7_electricity.solver import solve_board, solve_label_maps


TARGET_BOARD_MAP = {
    "1x1": ["right", "down"],
    "1x2": ["left", "right"],
    "1x3": ["left", "down"],
    "2x1": ["up", "down"],
    "2x2": ["up", "right", "down"],
    "2x3": ["up", "left"],
    "3x1": ["up", "right"],
    "3x2": ["left", "right", "down"],
    "3x3": ["up", "left"],
}

CURRENT_BOARD_MAP = {
    "1x1": ["up", "right"],
    "1x2": ["left", "right"],
    "1x3": ["left", "down"],
    "2x1": ["up", "down"],
    "2x2": ["right", "down", "left"],
    "2x3": ["up", "left"],
    "3x1": ["up", "right"],
    "3x2": ["up", "right", "left"],
    "3x3": ["up", "left"],
}


# This test case verifies deterministic tile rotation helpers.
class RotationHelpersTest(unittest.TestCase):
    # This test verifies a single direction rotates clockwise across all edges.
    def test_rotate_direction_clockwise_moves_through_all_edges(self) -> None:
        self.assertEqual(rotate_direction_clockwise(Direction.UP, 0), Direction.UP)
        self.assertEqual(rotate_direction_clockwise(Direction.UP, 1), Direction.RIGHT)
        self.assertEqual(rotate_direction_clockwise(Direction.UP, 2), Direction.DOWN)
        self.assertEqual(rotate_direction_clockwise(Direction.UP, 3), Direction.LEFT)
        self.assertEqual(rotate_direction_clockwise(Direction.UP, 4), Direction.UP)

    # This test verifies a corner tile rotates into the expected next shape.
    def test_rotate_tile_clockwise_rotates_corner_tile(self) -> None:
        tile = Tile.from_exit_names(["up", "right"])

        rotated_tile = rotate_tile_clockwise(tile, 1)

        self.assertEqual(rotated_tile.to_exit_names(), ["right", "down"])

    # This test verifies a T-junction keeps three exits after rotation.
    def test_rotate_tile_clockwise_rotates_t_junction(self) -> None:
        tile = Tile.from_exit_names(["up", "right", "down"])

        rotated_tile = rotate_tile_clockwise(tile, 3)

        self.assertEqual(rotated_tile.to_exit_names(), ["up", "right", "left"])
        self.assertEqual(rotated_tile.exit_count, 3)

    # This test verifies repeated symmetric rotations are collapsed to unique shapes.
    def test_generate_tile_rotations_returns_unique_orientations(self) -> None:
        straight_tile = Tile.from_exit_names(["left", "right"])
        corner_tile = Tile.from_exit_names(["up", "right"])

        straight_rotations = [tile.to_exit_names() for tile in generate_tile_rotations(straight_tile)]
        corner_rotations = [tile.to_exit_names() for tile in generate_tile_rotations(corner_tile)]

        self.assertEqual(straight_rotations, [["right", "left"], ["up", "down"]])
        self.assertEqual(
            corner_rotations,
            [
                ["up", "right"],
                ["right", "down"],
                ["down", "left"],
                ["up", "left"],
            ],
        )

    # This test verifies the minimal clockwise turn count is returned when possible.
    def test_find_clockwise_turns_to_match_returns_minimal_turns(self) -> None:
        source_tile = Tile.from_exit_names(["up", "right"])
        target_tile = Tile.from_exit_names(["left", "up"])

        turns = find_clockwise_turns_to_match(source_tile, target_tile)

        self.assertEqual(turns, 3)

    # This test verifies incompatible tile shapes do not report a rotation solution.
    def test_find_clockwise_turns_to_match_returns_none_for_incompatible_shapes(self) -> None:
        source_tile = Tile.from_exit_names(["up", "right"])
        target_tile = Tile.from_exit_names(["up", "right", "down"])

        turns = find_clockwise_turns_to_match(source_tile, target_tile)

        self.assertIsNone(turns)


# This test case verifies deterministic solving from hand-written board maps.
class BoardSolverTest(unittest.TestCase):
    # This method builds the shared target board used by solver tests.
    def make_target_board(self) -> Board:
        return Board.from_label_map(TARGET_BOARD_MAP)

    # This method builds the shared current board used by solver tests.
    def make_current_board(self) -> Board:
        return Board.from_label_map(CURRENT_BOARD_MAP)

    # This test verifies the solver returns a stable per-tile rotation plan.
    def test_solve_board_returns_expected_rotation_map(self) -> None:
        plan = solve_board(self.make_current_board(), self.make_target_board())

        self.assertEqual(
            plan.to_rotation_map(),
            {
                "1x1": 1,
                "1x2": 0,
                "1x3": 0,
                "2x1": 0,
                "2x2": 3,
                "2x3": 0,
                "3x1": 0,
                "3x2": 2,
                "3x3": 0,
            },
        )
        self.assertEqual(plan.total_rotations, 6)

    # This test verifies the flat sequence matches the one-request-per-turn Hub contract.
    def test_solve_board_returns_expected_rotation_sequence(self) -> None:
        plan = solve_board(self.make_current_board(), self.make_target_board())

        self.assertEqual(
            plan.rotation_sequence,
            ["1x1", "2x2", "2x2", "2x2", "3x2", "3x2"],
        )
        self.assertEqual(
            [tile_plan.coordinate_label for tile_plan in plan.changed_tile_plans],
            ["1x1", "2x2", "3x2"],
        )

    # This test verifies an already solved board produces no outgoing rotations.
    def test_solve_board_returns_empty_sequence_for_solved_board(self) -> None:
        board = self.make_target_board()

        plan = solve_board(board, board)

        self.assertEqual(plan.total_rotations, 0)
        self.assertEqual(plan.rotation_sequence, [])
        self.assertEqual(plan.changed_tile_plans, ())

    # This test verifies the label-map shortcut builds boards and solves them correctly.
    def test_solve_label_maps_matches_board_solver_result(self) -> None:
        plan = solve_label_maps(CURRENT_BOARD_MAP, TARGET_BOARD_MAP)

        self.assertEqual(plan.total_rotations, 6)
        self.assertEqual(plan.rotation_sequence, ["1x1", "2x2", "2x2", "2x2", "3x2", "3x2"])

    # This test verifies impossible target shapes fail with a clear coordinate error.
    def test_solve_board_raises_for_impossible_tile_match(self) -> None:
        impossible_target_map = dict(TARGET_BOARD_MAP)
        impossible_target_map["1x1"] = ["up", "down"]

        with self.assertRaisesRegex(ValueError, "1x1"):
            solve_board(self.make_current_board(), Board.from_label_map(impossible_target_map))


if __name__ == "__main__":
    unittest.main()
