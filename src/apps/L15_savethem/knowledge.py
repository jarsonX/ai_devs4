# Deterministic validation and normalization of explored mission knowledge.

from __future__ import annotations

import re
from typing import Any

from src.apps.L15_savethem.models import ApiObservation, ExplorationResult, MissionKnowledge, VehicleSpec


TREE_FUEL_PATTERN = re.compile(r"additional\s+([0-9]+(?:\.[0-9]+)?)\s+units", re.IGNORECASE)
VALID_KEYWORDS_PATTERN = re.compile(r"Valid keywords are\s+(.+?)\.", re.IGNORECASE)


# Return one observation by id or fail with a clear message.
def get_observation_by_id(observations: tuple[ApiObservation, ...], observation_id: str) -> ApiObservation:
    for observation in observations:
        if observation.observation_id == observation_id:
            return observation
    raise ValueError(f"Unknown observation id: {observation_id}")


# Parse the 10x10 map and locate start plus goal markers.
def parse_map_observation(observation: ApiObservation) -> tuple[tuple[str, ...], int, int, int, int]:
    payload = observation.response.payload
    if not observation.ok or not isinstance(payload, dict):
        raise ValueError("Map observation is not a successful JSON payload.")
    raw_map = payload.get("map")
    if not isinstance(raw_map, list) or len(raw_map) != 10:
        raise ValueError("Map observation must contain a 10x10 grid.")

    map_rows: list[str] = []
    start: tuple[int, int] | None = None
    goal: tuple[int, int] | None = None

    for row_index, raw_row in enumerate(raw_map, start=1):
        if not isinstance(raw_row, list) or len(raw_row) != 10:
            raise ValueError("Every map row must contain exactly 10 cells.")
        row_text = "".join(str(cell) for cell in raw_row)
        map_rows.append(row_text)
        for col_index, cell in enumerate(raw_row, start=1):
            marker = str(cell)
            if marker == "S":
                start = (row_index, col_index)
            if marker == "G":
                goal = (row_index, col_index)

    if start is None or goal is None:
        raise ValueError("Map observation must contain both S and G markers.")

    return tuple(map_rows), start[0], start[1], goal[0], goal[1]


# Parse one vehicle observation into the internal vehicle profile.
def parse_vehicle_observation(observation: ApiObservation, expected_mode: str) -> VehicleSpec:
    payload = observation.response.payload
    if not observation.ok or not isinstance(payload, dict):
        raise ValueError(f"Vehicle observation for {expected_mode} is not a successful JSON payload.")
    name = str(payload.get("name", "")).strip()
    if name != expected_mode:
        raise ValueError(
            f"Vehicle observation {observation.observation_id} returned {name!r}, expected {expected_mode!r}."
        )
    consumption = payload.get("consumption")
    if not isinstance(consumption, dict):
        raise ValueError(f"Vehicle observation for {expected_mode} is missing consumption.")
    fuel = float(consumption.get("fuel"))
    food = float(consumption.get("food"))
    return VehicleSpec(
        mode=expected_mode,
        fuel_per_move=fuel,
        food_per_move=food,
        note=str(payload.get("note", "")).strip(),
    )


# Collect notes from every referenced support observation.
def collect_supporting_notes(
    observations: tuple[ApiObservation, ...],
    observation_ids: tuple[str, ...],
) -> list[dict[str, Any]]:
    collected_notes: list[dict[str, Any]] = []
    for observation_id in observation_ids:
        observation = get_observation_by_id(observations, observation_id)
        payload = observation.response.payload
        if not isinstance(payload, dict):
            continue
        notes = payload.get("notes", [])
        if not isinstance(notes, list):
            continue
        for note in notes:
            if isinstance(note, dict):
                collected_notes.append(note)
    return collected_notes


# Parse the valid command set from the supporting note corpus.
def parse_commands_from_notes(notes: list[dict[str, Any]]) -> tuple[str, ...]:
    for note in notes:
        content = str(note.get("content", ""))
        match = VALID_KEYWORDS_PATTERN.search(content)
        if match is None:
            continue
        commands = [
            item.strip()
            for item in match.group(1).split(",")
            if item.strip()
        ]
        if commands:
            return tuple(commands)
    raise ValueError("Could not parse valid command keywords from supporting notes.")


# Parse terrain and resource rules from the supporting note corpus.
def parse_rules_from_notes(notes: list[dict[str, Any]]) -> dict[str, Any]:
    note_ids_used = set()
    water_allowed_modes: set[str] = set()
    tree_additional_fuel: float | None = None
    rock_blocks_all = False
    resources_consumed_on_move = False
    vehicle_selected_at_departure = False
    dismount_allowed = False

    for note in notes:
        note_id = str(note.get("id", "")).strip()
        content = str(note.get("content", ""))
        lowered_content = content.lower()

        if "rocks that block movement completely" in lowered_content or (
            "block movement completely" in lowered_content and " r marks rocks" in lowered_content
        ):
            rock_blocks_all = True
            if note_id:
                note_ids_used.add(note_id)

        if "no vehicle except the horse can move through water safely" in lowered_content:
            water_allowed_modes.update({"horse", "walk"})
            if note_id:
                note_ids_used.add(note_id)

        if "car is not suitable for water" in lowered_content or "car cannot" in lowered_content:
            if note_id:
                note_ids_used.add(note_id)

        if "rocket should not be trusted there" in lowered_content or "cannot travel over water" in lowered_content:
            if note_id:
                note_ids_used.add(note_id)

        if "entering a tile marked with t increases fuel consumption" in lowered_content:
            match = TREE_FUEL_PATTERN.search(content)
            if match is None:
                raise ValueError("Tree penalty note exists but the numeric penalty could not be parsed.")
            tree_additional_fuel = float(match.group(1))
            if note_id:
                note_ids_used.add(note_id)

        if "fuel and food are consumed at the moment the traveler moves" in lowered_content:
            resources_consumed_on_move = True
            if note_id:
                note_ids_used.add(note_id)

        if "vehicle can be selected only at the very beginning" in lowered_content or (
            "vehicle has to be chosen at departure" in lowered_content
        ):
            vehicle_selected_at_departure = True
            if note_id:
                note_ids_used.add(note_id)

        if "command used for that action is dismount" in lowered_content or (
            "special transition command" in lowered_content and "dismount" in lowered_content
        ):
            dismount_allowed = True
            if note_id:
                note_ids_used.add(note_id)

    if tree_additional_fuel is None:
        raise ValueError("Missing tree fuel-penalty note in the supporting observations.")
    if not water_allowed_modes:
        raise ValueError("Missing water traversal note in the supporting observations.")
    if not rock_blocks_all:
        raise ValueError("Missing rock blocking rule in the supporting observations.")
    if not resources_consumed_on_move:
        raise ValueError("Missing resource-consumption timing rule in the supporting observations.")
    if not vehicle_selected_at_departure:
        raise ValueError("Missing vehicle-selection-at-departure rule in the supporting observations.")
    if not dismount_allowed:
        raise ValueError("Missing dismount rule in the supporting observations.")

    return {
        "water_allowed_modes": tuple(sorted(water_allowed_modes)),
        "tree_additional_fuel": tree_additional_fuel,
        "rock_blocks_all": rock_blocks_all,
        "resources_consumed_on_move": resources_consumed_on_move,
        "vehicle_selected_at_departure": vehicle_selected_at_departure,
        "dismount_allowed": dismount_allowed,
        "note_ids_used": tuple(sorted(note_ids_used)),
    }


# Build normalized mission knowledge from the exploration finish payload.
def build_mission_knowledge(exploration_result: ExplorationResult) -> MissionKnowledge:
    if exploration_result.status != "ready":
        raise ValueError("Exploration did not finish with ready status.")
    if not exploration_result.destination_city:
        raise ValueError("Ready exploration result is missing destination_city.")
    if not exploration_result.map_observation_id:
        raise ValueError("Ready exploration result is missing map observation.")

    map_observation = get_observation_by_id(
        exploration_result.observations,
        exploration_result.map_observation_id,
    )
    map_rows, start_row, start_col, goal_row, goal_col = parse_map_observation(map_observation)

    required_modes = ("walk", "horse", "car", "rocket")
    vehicles: dict[str, VehicleSpec] = {}
    for mode in required_modes:
        observation_id = exploration_result.vehicle_observation_ids.get(mode)
        if not observation_id:
            raise ValueError(f"Ready exploration result is missing vehicle observation for {mode}.")
        observation = get_observation_by_id(exploration_result.observations, observation_id)
        vehicles[mode] = parse_vehicle_observation(observation, mode)

    notes = collect_supporting_notes(
        exploration_result.observations,
        exploration_result.supporting_observation_ids,
    )
    commands = parse_commands_from_notes(notes)
    parsed_rules = parse_rules_from_notes(notes)

    return MissionKnowledge(
        destination_city=exploration_result.destination_city,
        map_rows=map_rows,
        start_row=start_row,
        start_col=start_col,
        goal_row=goal_row,
        goal_col=goal_col,
        vehicles=vehicles,
        commands=commands,
        water_allowed_modes=parsed_rules["water_allowed_modes"],
        powered_modes=("car", "rocket"),
        rock_blocks_all=parsed_rules["rock_blocks_all"],
        tree_additional_fuel=parsed_rules["tree_additional_fuel"],
        resources_consumed_on_move=parsed_rules["resources_consumed_on_move"],
        vehicle_selected_at_departure=parsed_rules["vehicle_selected_at_departure"],
        dismount_allowed=parsed_rules["dismount_allowed"],
        note_ids_used=parsed_rules["note_ids_used"],
    )


# Try to recover a ready exploration result from observed successful responses.
def attempt_ready_recovery(exploration_result: ExplorationResult) -> ExplorationResult | None:
    if exploration_result.status == "ready":
        return exploration_result

    destination_city: str | None = None
    map_observation_id: str | None = None
    vehicle_observation_ids: dict[str, str] = {}
    supporting_observation_ids: list[str] = []

    for observation in exploration_result.observations:
        if not observation.ok or not isinstance(observation.response.payload, dict):
            continue
        payload = observation.response.payload

        if observation.tool_name == "maps":
            city_name = str(payload.get("cityName", "")).strip()
            if city_name:
                destination_city = city_name
                map_observation_id = observation.observation_id

        if observation.tool_name == "wehicles":
            mode = str(payload.get("name", "")).strip()
            if mode in ("walk", "horse", "car", "rocket"):
                vehicle_observation_ids[mode] = observation.observation_id

        if observation.tool_name == "books":
            supporting_observation_ids.append(observation.observation_id)

    if not destination_city or not map_observation_id:
        return None

    for required_mode in ("walk", "horse", "car", "rocket"):
        if required_mode not in vehicle_observation_ids:
            return None

    if not supporting_observation_ids:
        return None

    recovered_result = ExplorationResult(
        status="ready",
        destination_city=destination_city,
        map_observation_id=map_observation_id,
        vehicle_observation_ids=vehicle_observation_ids,
        supporting_observation_ids=tuple(supporting_observation_ids),
        reason="deterministic recovery assembled a complete exploration summary from observed successful responses",
        unknowns=(),
        observations=exploration_result.observations,
        discovered_tools=exploration_result.discovered_tools,
        tool_trace=exploration_result.tool_trace,
        model_calls_used=exploration_result.model_calls_used,
        tool_calls_used=exploration_result.tool_calls_used,
        stop_reason=exploration_result.stop_reason,
        raw_final_text=exploration_result.raw_final_text,
        runtime_summary=exploration_result.runtime_summary,
    )

    try:
        build_mission_knowledge(recovered_result)
    except ValueError:
        return None

    return recovered_result
