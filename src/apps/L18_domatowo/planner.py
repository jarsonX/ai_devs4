# Map parsing and route planning for the L18 Domatowo workflow.

from __future__ import annotations

from collections import deque
from itertools import permutations
from typing import Any

from src.apps.L18_domatowo.models import Field, TargetGroup, TransportPlan


ROAD_TILE = "road"
SPAWN_FIELDS = (Field(5, 0), Field(5, 1), Field(5, 2), Field(5, 3))


# Convert a Hub coordinate label such as A6 into a Field.
def parse_field_label(label: str) -> Field:
    stripped = str(label).strip().upper()
    if len(stripped) < 2:
        raise ValueError(f"Invalid field label: {label!r}")
    col = ord(stripped[0]) - ord("A")
    row = int(stripped[1:]) - 1
    if row < 0 or col < 0:
        raise ValueError(f"Invalid field label: {label!r}")
    return Field(row=row, col=col)


# Return four-neighbor fields inside the map bounds.
def neighbors(field: Field, *, size: int) -> list[Field]:
    candidates = (
        Field(field.row - 1, field.col),
        Field(field.row + 1, field.col),
        Field(field.row, field.col - 1),
        Field(field.row, field.col + 1),
    )
    return [
        candidate
        for candidate in candidates
        if 0 <= candidate.row < size and 0 <= candidate.col < size
    ]


# Measure orthogonal walking distance for scouts.
def manhattan_distance(left: Field, right: Field) -> int:
    return abs(left.row - right.row) + abs(left.col - right.col)


# Parse the grid from a Hub getMap response.
def extract_grid(map_payload: dict[str, Any]) -> list[list[str]]:
    map_data = map_payload.get("map", map_payload)
    grid = map_data.get("grid")
    if not isinstance(grid, list) or not grid:
        raise ValueError("Map payload does not contain a non-empty grid.")
    parsed_grid: list[list[str]] = []
    for row in grid:
        if not isinstance(row, list):
            raise ValueError("Map grid rows must be lists.")
        parsed_grid.append([str(tile) for tile in row])
    return parsed_grid


# Find all cells with the highest numbered block terrain.
def find_highest_block_fields(grid: list[list[str]]) -> tuple[Field, ...]:
    highest_level = -1
    fields: list[Field] = []
    for row_index, row in enumerate(grid):
        for col_index, tile_name in enumerate(row):
            if not tile_name.startswith("block"):
                continue
            suffix = tile_name.removeprefix("block")
            if not suffix.isdigit():
                continue
            level = int(suffix)
            field = Field(row=row_index, col=col_index)
            if level > highest_level:
                highest_level = level
                fields = [field]
            elif level == highest_level:
                fields.append(field)
    if not fields:
        raise ValueError("Map does not contain any block terrain.")
    return tuple(sorted(fields))


# Group high-block cells into connected four-neighbor components.
def group_connected_targets(targets: tuple[Field, ...], *, size: int) -> list[TargetGroup]:
    remaining = set(targets)
    groups: list[TargetGroup] = []
    while remaining:
        start = min(remaining)
        remaining.remove(start)
        queue: deque[Field] = deque([start])
        component = [start]
        while queue:
            current = queue.popleft()
            for neighbor in neighbors(current, size=size):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
                    component.append(neighbor)
        groups.append(TargetGroup(targets=tuple(sorted(component))))
    return sorted(groups, key=lambda group: min(group.targets))


# Find shortest road-only distances from one road field.
def road_distances(grid: list[list[str]], start: Field) -> dict[Field, int]:
    size = len(grid)
    if grid[start.row][start.col] != ROAD_TILE:
        raise ValueError(f"Road distance start is not a road: {start.label()}")
    distances = {start: 0}
    queue: deque[Field] = deque([start])
    while queue:
        current = queue.popleft()
        for neighbor in neighbors(current, size=size):
            if grid[neighbor.row][neighbor.col] != ROAD_TILE:
                continue
            if neighbor in distances:
                continue
            distances[neighbor] = distances[current] + 1
            queue.append(neighbor)
    return distances


# Estimate the walking cost needed for a small scout team to cover a target group.
def estimate_scout_steps(stop: Field, targets: tuple[Field, ...], passengers: int) -> int:
    if passengers < 1:
        raise ValueError("passengers must be positive.")
    virtual_positions = [stop for _ in range(passengers)]
    remaining = set(targets)
    total_steps = 0
    while remaining:
        best_pair: tuple[int, int, Field] | None = None
        for scout_index, position in enumerate(virtual_positions):
            for target in remaining:
                distance = manhattan_distance(position, target)
                candidate = (distance, scout_index, target)
                if best_pair is None or candidate < best_pair:
                    best_pair = candidate
        if best_pair is None:
            break
        distance, scout_index, target = best_pair
        total_steps += distance
        virtual_positions[scout_index] = target
        remaining.remove(target)
    return total_steps


# Pick a practical scout count for one high-block group.
def passengers_for_group(group: TargetGroup) -> int:
    return max(1, min(4, (len(group.targets) + 1) // 2))


# Choose a road stop that minimizes road travel plus estimated scout walking.
def choose_stop_for_group(
    grid: list[list[str]],
    spawn: Field,
    group: TargetGroup,
    passengers: int,
) -> TransportPlan:
    distances = road_distances(grid, spawn)
    best_plan: TransportPlan | None = None
    for stop, road_steps in distances.items():
        scout_steps = estimate_scout_steps(stop, group.targets, passengers)
        estimated_cost = road_steps + (scout_steps * 7) + len(group.targets)
        plan = TransportPlan(
            spawn=spawn,
            stop=stop,
            targets=group.targets,
            passengers=passengers,
            estimated_cost=estimated_cost,
        )
        if best_plan is None or plan.estimated_cost < best_plan.estimated_cost:
            best_plan = plan
    if best_plan is None:
        raise ValueError(f"No road stop is reachable from {spawn.label()}.")
    return best_plan


# Build transporter plans for all high-block groups within unit limits.
def build_transport_plans(
    grid: list[list[str]],
    *,
    transporter_limit: int,
    scout_limit: int,
) -> list[TransportPlan]:
    targets = find_highest_block_fields(grid)
    groups = group_connected_targets(targets, size=len(grid))
    if len(groups) > transporter_limit:
        raise ValueError("More target groups than available transporters.")

    group_passengers = [passengers_for_group(group) for group in groups]
    if sum(group_passengers) > scout_limit:
        raise ValueError("Target groups need more scouts than the limit allows.")

    available_spawns = SPAWN_FIELDS[: len(groups)]
    best_plans: list[TransportPlan] | None = None
    best_cost: int | None = None
    for ordered_groups in permutations(groups):
        plans = [
            choose_stop_for_group(grid, spawn, group, passengers_for_group(group))
            for spawn, group in zip(available_spawns, ordered_groups, strict=True)
        ]
        cost = sum(plan.estimated_cost for plan in plans)
        if best_cost is None or cost < best_cost:
            best_cost = cost
            best_plans = plans
    if best_plans is None:
        raise ValueError("No transport plan could be built.")
    return best_plans
