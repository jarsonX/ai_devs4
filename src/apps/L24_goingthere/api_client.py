# Guarded HTTP client for the L24 goingthere task API.

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, Protocol, TypeVar

import requests

from src.apps.L24_goingthere.config import HubConfig, RuntimeConfig
from src.apps.L24_goingthere.models import (
    ApiResponse,
    GameState,
    LoggedExchange,
    MoveOutcome,
    MovementCommand,
    PreviewState,
    RadarReading,
    mask_request_payload,
)
from src.apps.L24_goingthere.parsing import (
    parse_hint_response,
    parse_move_response,
    parse_preview_response,
    parse_scanner_response,
    parse_start_response,
    payload_error_code,
)
from src.apps.L24_goingthere.planner import destination_row


ParsedValue = TypeVar("ParsedValue")


# Define the requests.Session operation used by the client.
class SessionProtocol(Protocol):
    # Send one HTTP request through an injected session.
    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        ...


# Signal that one bounded API operation could not produce a valid response.
class OperationRetryError(RuntimeError):
    pass


# Signal that a movement result cannot be reconciled safely.
class AmbiguousMoveError(RuntimeError):
    pass


# Convert a requests response into the app's stable response model.
def build_api_response(response: requests.Response) -> ApiResponse:
    try:
        payload: Any | None = response.json()
    except (requests.JSONDecodeError, ValueError):
        payload = None
    return ApiResponse(
        status_code=response.status_code,
        payload=payload,
        text=response.text,
    )


# Send guarded requests and validate state-changing responses before returning.
class GoingThereClient:
    # Store connection settings, injected dependencies, and request audit state.
    def __init__(
        self,
        hub_config: HubConfig,
        runtime_config: RuntimeConfig,
        *,
        session: SessionProtocol | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.hub_config = hub_config
        self.runtime_config = runtime_config
        self.session = session or requests.Session()
        self.sleep = sleep
        self._request_count = 0
        self._exchanges: list[LoggedExchange] = []

    # Return the total number of actual HTTP attempts.
    def request_count(self) -> int:
        return self._request_count

    # Return a copy of masked request and response audit records.
    def exchanges(self) -> list[LoggedExchange]:
        return list(self._exchanges)

    # Calculate a bounded exponential delay, with extra space after rate limiting.
    def _backoff_seconds(self, attempt: int, response: ApiResponse | None) -> float:
        delay = min(
            self.runtime_config.base_backoff_seconds * (2 ** (attempt - 1)),
            self.runtime_config.max_backoff_seconds,
        )
        if response is not None and response.status_code == 429:
            delay = max(delay, 5.0)
        return delay

    # Preserve only masked request metadata for one HTTP attempt.
    def _masked_request(
        self,
        method: str,
        *,
        json_payload: dict[str, Any] | None,
        params: dict[str, Any] | None,
        form_data: dict[str, Any] | None,
    ) -> dict[str, Any]:
        request: dict[str, Any] = {"method": method.upper()}
        if json_payload is not None:
            request["json"] = mask_request_payload(json_payload)
        if params is not None:
            request["params"] = mask_request_payload(params)
        if form_data is not None:
            request["form"] = mask_request_payload(form_data)
        return request

    # Execute one HTTP attempt and convert transport failures into auditable responses.
    def _send_once(
        self,
        action: str,
        attempt: int,
        method: str,
        url: str,
        *,
        json_payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        form_data: dict[str, Any] | None = None,
    ) -> ApiResponse:
        self._request_count += 1
        if self._request_count > self.runtime_config.max_total_requests:
            raise OperationRetryError("The total HTTP request guard was exceeded.")

        try:
            raw_response = self.session.request(
                method,
                url,
                json=json_payload,
                params=params,
                data=form_data,
                timeout=self.runtime_config.request_timeout_seconds,
            )
            response = build_api_response(raw_response)
        except requests.RequestException as error:
            response = ApiResponse(
                status_code=0,
                payload=None,
                text=f"transport_error:{type(error).__name__}",
            )

        self._exchanges.append(
            LoggedExchange(
                sequence=self._request_count,
                action=action,
                attempt=attempt,
                request=self._masked_request(
                    method,
                    json_payload=json_payload,
                    params=params,
                    form_data=form_data,
                ),
                response=response,
            )
        )
        return response

    # Retry a read-like or explicitly idempotent operation until parsing succeeds.
    def _retry_parsed(
        self,
        *,
        action: str,
        method: str,
        url: str,
        parser: Callable[[ApiResponse], ParsedValue],
        json_payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        form_data: dict[str, Any] | None = None,
    ) -> ParsedValue:
        last_error: Exception | None = None
        for attempt in range(1, self.runtime_config.max_operation_attempts + 1):
            response = self._send_once(
                action,
                attempt,
                method,
                url,
                json_payload=json_payload,
                params=params,
                form_data=form_data,
            )
            try:
                return parser(response)
            except ValueError as error:
                last_error = error
                if attempt < self.runtime_config.max_operation_attempts:
                    self.sleep(self._backoff_seconds(attempt, response))

        raise OperationRetryError(
            f"{action} did not produce a valid response within "
            f"{self.runtime_config.max_operation_attempts} attempts."
        ) from last_error

    # Start one new game and return its server-confirmed state.
    def start_game(self) -> GameState:
        payload = {
            "apikey": self.hub_config.api_key,
            "task": self.hub_config.task_name,
            "answer": {"command": "start"},
        }
        return self._retry_parsed(
            action="command:start",
            method="POST",
            url=self.hub_config.verify_url,
            json_payload=payload,
            parser=parse_start_response,
        )

    # Query and parse the distorted frequency scanner.
    def scan_radar(self) -> RadarReading:
        return self._retry_parsed(
            action="frequency_scan",
            method="GET",
            url=f"{self.hub_config.base_url}/api/frequencyScanner",
            params={"key": self.hub_config.api_key},
            parser=parse_scanner_response,
        )

    # Disarm one detected radar trap and require explicit confirmation.
    def disarm_radar(self, *, frequency: int, disarm_hash: str) -> ApiResponse:
        payload = {
            "apikey": self.hub_config.api_key,
            "frequency": frequency,
            "disarmHash": disarm_hash,
        }

        # Validate that the trap endpoint explicitly confirms disarming.
        def parse_disarm(response: ApiResponse) -> ApiResponse:
            message = (
                response.payload.get("message")
                if isinstance(response.payload, dict)
                else None
            )
            if (
                response.status_code == 200
                and isinstance(message, str)
                and "disarmed" in message.lower()
            ):
                return response
            raise ValueError("Radar endpoint did not confirm disarming.")

        return self._retry_parsed(
            action="radar_disarm",
            method="POST",
            url=f"{self.hub_config.base_url}/api/frequencyScanner",
            json_payload=payload,
            parser=parse_disarm,
        )

    # Fetch one non-empty radio hint without interpreting its language.
    def get_hint(self) -> str:
        return self._retry_parsed(
            action="radio_hint",
            method="POST",
            url=f"{self.hub_config.base_url}/api/getmessage",
            json_payload={"apikey": self.hub_config.api_key},
            parser=parse_hint_response,
        )

    # Read the official preview state for ambiguous movement reconciliation.
    def get_preview_state(self) -> PreviewState:
        return self._retry_parsed(
            action="preview_state",
            method="POST",
            url=f"{self.hub_config.base_url}/goingthere_backend",
            form_data={"key": self.hub_config.api_key, "after_event_id": "0"},
            parser=parse_preview_response,
        )

    # Convert a preview snapshot into a movement result after an ambiguous response.
    def _reconcile_move(
        self,
        before: GameState,
        command: MovementCommand,
        ambiguous_response: ApiResponse,
    ) -> MoveOutcome | None:
        preview = self.get_preview_state()
        if preview.finished:
            return MoveOutcome(
                state=preview.state,
                crashed=False,
                finished=True,
                flag=preview.flag,
                response=ambiguous_response,
                reconciled_from_preview=True,
            )
        if preview.crashed:
            return MoveOutcome(
                state=None,
                crashed=True,
                finished=False,
                flag=preview.flag,
                response=ambiguous_response,
                reconciled_from_preview=True,
            )
        if preview.state is None:
            raise AmbiguousMoveError("Preview state has no usable player position.")

        expected_row = destination_row(before.player_row, command)
        if (
            preview.state.player_col == before.player_col + 1
            and preview.state.player_row == expected_row
        ):
            return MoveOutcome(
                state=preview.state,
                crashed=False,
                finished=preview.state.player_col == 12,
                flag=preview.flag,
                response=ambiguous_response,
                reconciled_from_preview=True,
            )
        if (
            preview.state.player_col == before.player_col
            and preview.state.player_row == before.player_row
        ):
            return None

        raise AmbiguousMoveError(
            "Preview state does not match either the pre-move or expected post-move state."
        )

    # Submit one movement command without blindly duplicating an ambiguous write.
    def move(
        self,
        command: MovementCommand,
        *,
        before: GameState,
    ) -> MoveOutcome:
        payload = {
            "apikey": self.hub_config.api_key,
            "task": self.hub_config.task_name,
            "answer": {"command": command.value},
        }
        last_error: Exception | None = None

        for attempt in range(1, self.runtime_config.max_operation_attempts + 1):
            response = self._send_once(
                f"command:{command.value}",
                attempt,
                "POST",
                self.hub_config.verify_url,
                json_payload=payload,
            )
            try:
                return parse_move_response(response, base_row=before.base_row)
            except ValueError as error:
                last_error = error

            error_code = payload_error_code(response.payload)
            is_explicit_retry = response.status_code == 429 or (
                error_code is not None and error_code != -950
            )
            is_ambiguous = response.status_code == 0 or response.status_code >= 500

            if is_ambiguous:
                reconciled = self._reconcile_move(before, command, response)
                if reconciled is not None:
                    return reconciled
            elif not is_explicit_retry:
                raise AmbiguousMoveError(
                    "Movement was rejected without a retryable or terminal game result."
                ) from last_error

            if attempt < self.runtime_config.max_operation_attempts:
                self.sleep(self._backoff_seconds(attempt, response))

        raise OperationRetryError(
            f"Movement {command.value} was not resolved within "
            f"{self.runtime_config.max_operation_attempts} attempts."
        ) from last_error
