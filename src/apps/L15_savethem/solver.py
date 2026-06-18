# Deterministic route solving and simulation for the L15 mission.

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush

from src.apps.L15_savethem.models import MissionKnowledge, RoutePlan


COMMAND_DELTAS = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}
RESOURCE_SCALE = 10


# Store the scaled route state used by the Dijkstra-like search.
@dataclass(frozen=True)
class RouteState:
    row: int
    col: int
    mode: str
    fuel_tenths: int
    food_tenths: int


# Convert one decimal resource value into a stable scaled integer.
def to_tenths(value: float) -> int:
    return int(round(value * RESOURCE_SCALE))


# Convert one scaled resource value back into a display float.
def from_tenths(value: int) -> float:
    return value / RESOURCE_SCALE


# Return the terrain marker at one 1-based map position.
def terrain_at(knowledge: MissionKnowledge, row: int, col: int) -> str:
    return knowledge.map_rows[row - 1][col - 1]


# Check whether one coordinate lies inside the 10x10 map.
def in_bounds(knowledge: MissionKnowledge, row: int, col: int) -> bool:
    return 1 <= row <= len(knowledge.map_rows) and 1 <= col <= len(knowledge.map_rows[0])


# Return the extra fuel cost applied when entering the target terrain.
def extra_fuel_cost_tenths(knowledge: MissionKnowledge, terrain: str, mode: str) -> int:
    if terrain == "T" and mode in knowledge.powered_modes:
        return to_tenths(knowledge.tree_additional_fuel)
    return 0


# Check whether one terrain tile can be entered in the current mode.
def can_enter_terrain(knowledge: MissionKnowledge, terrain: str, mode: str) -> bool:
    if terrain == "R" and knowledge.rock_blocks_all:
        return False
    if terrain == "W":
        return mode in knowledge.water_allowed_modes
    return True


# Simulate one command list and return the resulting route summary.
def simulate_route(
    knowledge: MissionKnowledge,
    commands: tuple[str, ...] | list[str],
    *,
    starting_fuel: float,
    starting_food: float,
) -> RoutePlan:
    if not commands:
        raise ValueError("Route commands must not be empty.")

    mode = commands[0]
    if mode not in knowledge.vehicles:
        raise ValueError(f"First command must be one of the known modes, got {mode!r}.")

    row = knowledge.start_row
    col = knowledge.start_col
    fuel_tenths = to_tenths(starting_fuel)
    food_tenths = to_tenths(starting_food)
    visited_positions = [(row, col)]

    for command in commands[1:]:
        if command == "dismount":
            if not knowledge.dismount_allowed:
                raise ValueError("dismount is not allowed by the mission rules.")
            if mode == "walk":
                raise ValueError("Cannot dismount while already in walk mode.")
            mode = "walk"
            continue

        if command not in COMMAND_DELTAS:
            raise ValueError(f"Unsupported movement command: {command!r}.")

        delta_row, delta_col = COMMAND_DELTAS[command]
        next_row = row + delta_row
        next_col = col + delta_col
        if not in_bounds(knowledge, next_row, next_col):
            raise ValueError("Route moves out of bounds.")

        terrain = terrain_at(knowledge, next_row, next_col)
        if not can_enter_terrain(knowledge, terrain, mode):
            raise ValueError(f"Mode {mode!r} cannot enter terrain {terrain!r}.")

        vehicle = knowledge.vehicles[mode]
        fuel_tenths -= to_tenths(vehicle.fuel_per_move) + extra_fuel_cost_tenths(
            knowledge,
            terrain,
            mode,
        )
        food_tenths -= to_tenths(vehicle.food_per_move)
        if fuel_tenths < 0 or food_tenths < 0:
            raise ValueError("Route runs out of resources before reaching the goal.")

        row = next_row
        col = next_col
        visited_positions.append((row, col))

    reached_goal = row == knowledge.goal_row and col == knowledge.goal_col
    return RoutePlan(
        commands=tuple(commands),
        final_row=row,
        final_col=col,
        remaining_fuel=from_tenths(fuel_tenths),
        remaining_food=from_tenths(food_tenths),
        fuel_spent=starting_fuel - from_tenths(fuel_tenths),
        food_spent=starting_food - from_tenths(food_tenths),
        reached_goal=reached_goal,
        visited_positions=tuple(visited_positions),
    )


# Compute one feasible route with lexicographic preference for lower food burn.
def solve_route(
    knowledge: MissionKnowledge,
    *,
    starting_fuel: float,
    starting_food: float,
) -> RoutePlan:
    start_fuel_tenths = to_tenths(starting_fuel)
    start_food_tenths = to_tenths(starting_food)
    initial_modes = ("walk", "horse", "car", "rocket")
    frontier: list[tuple[tuple[int, int, int], int, RouteState]] = []
    previous: dict[RouteState, tuple[RouteState | None, str]] = {}
    best_costs: dict[RouteState, tuple[int, int, int]] = {}
    sequence = 0

    for mode in initial_modes:
        state = RouteState(
            row=knowledge.start_row,
            col=knowledge.start_col,
            mode=mode,
            fuel_tenths=start_fuel_tenths,
            food_tenths=start_food_tenths,
        )
        cost = (0, 0, 0)
        best_costs[state] = cost
        previous[state] = (None, mode)
        heappush(frontier, (cost, sequence, state))
        sequence += 1

    goal_state: RouteState | None = None

    while frontier:
        cost, _sequence, state = heappop(frontier)
        if best_costs.get(state) != cost:
            continue

        if state.row == knowledge.goal_row and state.col == knowledge.goal_col:
            goal_state = state
            break

        if knowledge.dismount_allowed and state.mode != "walk":
            next_state = RouteState(
                row=state.row,
                col=state.col,
                mode="walk",
                fuel_tenths=state.fuel_tenths,
                food_tenths=state.food_tenths,
            )
            next_cost = (cost[0], cost[1], cost[2] + 1)
            if next_state not in best_costs or next_cost < best_costs[next_state]:
                best_costs[next_state] = next_cost
                previous[next_state] = (state, "dismount")
                heappush(frontier, (next_cost, sequence, next_state))
                sequence += 1

        for command, (delta_row, delta_col) in COMMAND_DELTAS.items():
            next_row = state.row + delta_row
            next_col = state.col + delta_col
            if not in_bounds(knowledge, next_row, next_col):
                continue

            terrain = terrain_at(knowledge, next_row, next_col)
            if not can_enter_terrain(knowledge, terrain, state.mode):
                continue

            vehicle = knowledge.vehicles[state.mode]
            fuel_delta = to_tenths(vehicle.fuel_per_move) + extra_fuel_cost_tenths(
                knowledge,
                terrain,
                state.mode,
            )
            food_delta = to_tenths(vehicle.food_per_move)
            next_fuel = state.fuel_tenths - fuel_delta
            next_food = state.food_tenths - food_delta
            if next_fuel < 0 or next_food < 0:
                continue

            next_state = RouteState(
                row=next_row,
                col=next_col,
                mode=state.mode,
                fuel_tenths=next_fuel,
                food_tenths=next_food,
            )
            next_cost = (
                cost[0] + food_delta,
                cost[1] + fuel_delta,
                cost[2] + 1,
            )
            if next_state not in best_costs or next_cost < best_costs[next_state]:
                best_costs[next_state] = next_cost
                previous[next_state] = (state, command)
                heappush(frontier, (next_cost, sequence, next_state))
                sequence += 1

    if goal_state is None:
        raise ValueError("No feasible route reaches the goal within the available resources.")

    command_reversed: list[str] = []
    current_state: RouteState | None = goal_state
    while current_state is not None:
        parent_state, command = previous[current_state]
        command_reversed.append(command)
        current_state = parent_state
    command_reversed.reverse()

    return simulate_route(
        knowledge,
        command_reversed,
        starting_fuel=starting_fuel,
        starting_food=starting_food,
    )

