# Guarded workflow with semantic hint classification and deterministic movement.

from __future__ import annotations

import hashlib
from dataclasses import asdict
from typing import Protocol

from src.apps.L24_goingthere.models import (
    GameState,
    LoggedExchange,
    MoveOutcome,
    MovementCommand,
    RadarClear,
    RadarReading,
    RadarTrap,
    RockDirection,
)
from src.apps.L24_goingthere.planner import choose_command, safe_commands


MAX_MOVES = 11
MAX_RADAR_CYCLES_PER_COLUMN = 4


# Define the client operations used by the workflow and offline tests.
class GoingThereClientProtocol(Protocol):
    # Start a new game.
    def start_game(self) -> GameState:
        ...

    # Query the current radar state.
    def scan_radar(self) -> RadarReading:
        ...

    # Disarm one radar trap.
    def disarm_radar(self, *, frequency: int, disarm_hash: str):
        ...

    # Fetch one raw next-column rock hint.
    def get_hint(self) -> str:
        ...

    # Submit one movement command.
    def move(
        self,
        command: MovementCommand,
        *,
        before: GameState,
    ) -> MoveOutcome:
        ...

    # Return the request count for reports.
    def request_count(self) -> int:
        ...

    # Return masked HTTP exchanges for reports.
    def exchanges(self) -> list[LoggedExchange]:
        ...


# Define the only semantic operation the workflow accepts from a model.
class RadioHintClassifierProtocol(Protocol):
    # Classify one raw hint into a validated relative rock direction.
    def classify(self, hint: str) -> RockDirection:
        ...

    # Return the number of bounded logical model requests.
    def request_count(self) -> int:
        ...


# Signal that a server-confirmed movement contradicted the local safety model.
class UnexpectedCrashError(RuntimeError):
    pass


# Calculate the task-specific SHA-1 value for one detection code.
def build_disarm_hash(detection_code: str) -> str:
    return hashlib.sha1(f"{detection_code}disarm".encode("utf-8")).hexdigest()


# Confirm the current column is clear, disarming and rechecking when necessary.
def secure_current_column(client: GoingThereClientProtocol) -> None:
    for _ in range(MAX_RADAR_CYCLES_PER_COLUMN):
        reading = client.scan_radar()
        if isinstance(reading, RadarClear):
            return
        if isinstance(reading, RadarTrap):
            client.disarm_radar(
                frequency=reading.frequency,
                disarm_hash=build_disarm_hash(reading.detection_code),
            )
    raise RuntimeError(
        "The current column was not confirmed clear within the radar cycle guard."
    )


# Execute one non-brute-force game and stop on any unexplained crash.
class GoingThereWorkflow:
    # Store the guarded API client and narrow semantic classifier.
    def __init__(
        self,
        client: GoingThereClientProtocol,
        classifier: RadioHintClassifierProtocol,
    ) -> None:
        self.client = client
        self.classifier = classifier

    # Run one game from start to victory or a diagnostic failure.
    def run(self) -> dict[str, object]:
        state = self.client.start_game()
        steps: list[dict[str, object]] = []

        for move_number in range(1, MAX_MOVES + 1):
            if state.player_col == 12:
                break

            secure_current_column(self.client)
            hint = self.client.get_hint()
            direction = self.classifier.classify(hint)
            available = safe_commands(state, direction)
            command = choose_command(state, direction)
            outcome = self.client.move(command, before=state)

            step = {
                "move_number": move_number,
                "before": asdict(state),
                "hint": hint,
                "next_rock_direction": direction.value,
                "safe_commands": [candidate.value for candidate in available],
                "selected_command": command.value,
                "crashed": outcome.crashed,
                "finished": outcome.finished,
                "reconciled_from_preview": outcome.reconciled_from_preview,
            }
            steps.append(step)

            if outcome.crashed:
                raise UnexpectedCrashError(
                    "The server reported a stone collision after the planner marked "
                    f"{command.value} safe. Diagnostic step: {step}"
                )
            if outcome.finished:
                return {
                    "status": "solved",
                    "flag": outcome.flag,
                    "final_state": asdict(outcome.state) if outcome.state else None,
                    "moves": steps,
                    "request_count": self.client.request_count(),
                    "model_request_count": self.classifier.request_count(),
                }
            if outcome.state is None:
                raise RuntimeError("Accepted movement returned no usable game state.")
            state = outcome.state

        raise RuntimeError("The move guard ended before the rocket reached column 12.")
