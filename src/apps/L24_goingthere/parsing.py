# Parsers for damaged scanner data and Hub game responses.

from __future__ import annotations

import re
from typing import Any

from src.apps.L24_goingthere.models import (
    ApiResponse,
    GameState,
    MoveOutcome,
    PreviewState,
    RadarClear,
    RadarReading,
    RadarTrap,
    extract_flag,
)


CLEAR_PATTERN = re.compile(r"c+l+e+a+r+")
FREQUENCY_PATTERN = re.compile(r":\s*[\"'`]?(\d{2,4})")
DETECTION_CODE_PATTERN = re.compile(
    r":\s*[\"'`]?([A-Za-z0-9]{6})(?=[\"'`,}\s])"
)
# Return whether an arbitrary JSON payload looks like an API-level failure.
def payload_error_code(payload: Any) -> int | None:
    if not isinstance(payload, dict):
        return None
    code = payload.get("code")
    return code if isinstance(code, int) and code < 0 else None


# Parse one current game-state object from a start or accepted-move payload.
def parse_game_state(payload: Any, *, fallback_base_row: int | None = None) -> GameState:
    if not isinstance(payload, dict):
        raise ValueError("Game response payload must be an object.")

    player = payload.get("player")
    current_column = payload.get("currentColumn")
    base = payload.get("base")
    if not isinstance(player, dict) or not isinstance(current_column, dict):
        raise ValueError("Game response is missing player or currentColumn.")

    base_row = fallback_base_row
    if isinstance(base, dict):
        base_row = base.get("row")
    if not isinstance(base_row, int):
        raise ValueError("Game response is missing the target base row.")

    player_row = player.get("row")
    player_col = player.get("col")
    stone_row = current_column.get("stoneRow")
    if not all(isinstance(value, int) for value in (player_row, player_col, stone_row)):
        raise ValueError("Game response contains invalid row or column values.")

    return GameState(
        player_row=player_row,
        player_col=player_col,
        base_row=base_row,
        current_stone_row=stone_row,
    )


# Parse and validate the response that starts a new game.
def parse_start_response(response: ApiResponse) -> GameState:
    if response.status_code != 200:
        raise ValueError(f"Start returned HTTP {response.status_code}.")
    if not isinstance(response.payload, dict) or response.payload.get("code") != 110:
        raise ValueError("Start response did not confirm a new game.")
    return parse_game_state(response.payload)


# Normalize distorted clear text or recover a radar trap from damaged JSON-like text.
def parse_scanner_response(response: ApiResponse) -> RadarReading:
    if response.status_code != 200:
        raise ValueError(f"Scanner returned HTTP {response.status_code}.")

    letters_only = re.sub(r"[^a-z]", "", response.text.lower())
    if CLEAR_PATTERN.search(letters_only):
        return RadarClear()

    frequency_matches = FREQUENCY_PATTERN.findall(response.text)
    code_matches = DETECTION_CODE_PATTERN.findall(response.text)
    if not frequency_matches or not code_matches:
        raise ValueError("Scanner response is neither clear nor a recoverable trap.")

    return RadarTrap(
        frequency=int(frequency_matches[0]),
        detection_code=code_matches[-1],
    )


# Extract one non-empty raw radio hint without interpreting its wording.
def parse_hint_response(response: ApiResponse) -> str:
    if response.status_code != 200:
        raise ValueError(f"Radio endpoint returned HTTP {response.status_code}.")
    if not isinstance(response.payload, dict):
        raise ValueError("Radio response payload must be an object.")
    hint = response.payload.get("hint")
    if not isinstance(hint, str) or not hint.strip():
        raise ValueError("Radio response contains no usable hint.")
    return hint.strip()


# Parse one movement response without guessing whether a rejected move succeeded.
def parse_move_response(response: ApiResponse, *, base_row: int) -> MoveOutcome:
    payload = response.payload
    flag = extract_flag(response)
    if isinstance(payload, dict) and payload.get("crashed") is True:
        return MoveOutcome(
            state=None,
            crashed=True,
            finished=False,
            flag=flag,
            response=response,
        )

    if response.status_code == 200 and flag is not None:
        state: GameState | None = None
        try:
            state = parse_game_state(payload, fallback_base_row=base_row)
        except ValueError:
            state = None
        return MoveOutcome(
            state=state,
            crashed=False,
            finished=True,
            flag=flag,
            response=response,
        )

    if response.status_code == 200 and isinstance(payload, dict) and "player" in payload:
        state = parse_game_state(payload, fallback_base_row=base_row)
        finished = state.player_col == 12 or flag is not None
        return MoveOutcome(
            state=state,
            crashed=False,
            finished=finished,
            flag=flag,
            response=response,
        )

    raise ValueError("Movement response did not confirm acceptance, crash, or victory.")


# Parse the official preview backend state used only for ambiguous move recovery.
def parse_preview_response(response: ApiResponse) -> PreviewState:
    if response.status_code != 200 or not isinstance(response.payload, dict):
        raise ValueError("Preview backend did not return a valid state object.")

    payload = response.payload
    active = bool(payload.get("active"))
    crashed = bool(payload.get("crashed"))
    finished = bool(payload.get("finished") or payload.get("victory"))
    flag_value = payload.get("flag") or payload.get("secretFlag")
    flag = flag_value if isinstance(flag_value, str) and flag_value.strip() else None

    state: GameState | None = None
    player = payload.get("player")
    map_rows = payload.get("map")
    base_row_zero = payload.get("baseRow")
    if (
        isinstance(player, dict)
        and isinstance(map_rows, list)
        and isinstance(base_row_zero, int)
    ):
        row_zero = player.get("row")
        col_zero = player.get("col")
        if isinstance(row_zero, int) and isinstance(col_zero, int):
            stone_row = None
            for candidate_row, map_row in enumerate(map_rows):
                if (
                    isinstance(map_row, list)
                    and col_zero < len(map_row)
                    and map_row[col_zero] == 1
                ):
                    stone_row = candidate_row + 1
                    break
            if stone_row is not None:
                state = GameState(
                    player_row=row_zero + 1,
                    player_col=col_zero + 1,
                    base_row=base_row_zero + 1,
                    current_stone_row=stone_row,
                )

    return PreviewState(
        state=state,
        active=active,
        crashed=crashed,
        finished=finished,
        flag=flag,
    )
