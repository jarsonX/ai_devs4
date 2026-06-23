# Guarded HTTP client for the L18 Domatowo Hub API.

from __future__ import annotations

from typing import Any, Protocol

import requests

from src.apps.L18_domatowo.config import HubConfig
from src.apps.L18_domatowo.models import ApiResponse, LoggedExchange


REDACTED = "***REDACTED***"


# Define the small subset of requests.Session used by the client.
class SessionProtocol(Protocol):
    # Send one POST request through an injected HTTP session.
    def post(self, *args: Any, **kwargs: Any) -> requests.Response:
        ...


# Read a JSON response when possible while keeping text fallback.
def build_api_response(response: requests.Response) -> ApiResponse:
    try:
        payload = response.json()
    except requests.JSONDecodeError:
        payload = None
    return ApiResponse(
        status_code=response.status_code,
        payload=payload,
        text=response.text,
    )


# Remove the API key before preserving a request in runtime data.
def mask_payload(payload: dict[str, Any]) -> dict[str, Any]:
    masked_payload = dict(payload)
    if "apikey" in masked_payload:
        masked_payload["apikey"] = REDACTED
    return masked_payload


# Send Domatowo task actions through one guarded HTTP session.
class DomatowoApiClient:
    # Store Hub config plus request timeout and request-count guard.
    def __init__(
        self,
        config: HubConfig,
        *,
        timeout_seconds: int,
        max_requests: int,
        session: SessionProtocol | None = None,
    ) -> None:
        self.hub_config = config
        self.timeout_seconds = timeout_seconds
        self.max_requests = max_requests
        self.session = session or requests.Session()
        self._request_count = 0

    # Return how many Hub requests have been used in this run.
    def request_count(self) -> int:
        return self._request_count

    # Send one validated action payload to the Hub.
    def call(self, answer: dict[str, Any]) -> LoggedExchange:
        action = str(answer.get("action", "")).strip()
        if not action:
            raise ValueError("Hub answer must include a non-empty action.")

        self._request_count += 1
        if self._request_count > self.max_requests:
            raise ValueError("The Hub request guard was exceeded.")

        payload = {
            "apikey": self.hub_config.api_key,
            "task": self.hub_config.task_name,
            "answer": answer,
        }
        response = self.session.post(
            self.hub_config.verify_url,
            json=payload,
            timeout=self.timeout_seconds,
        )
        return LoggedExchange(
            sequence=self._request_count,
            action=action,
            request=mask_payload(payload),
            response=build_api_response(response),
        )

    # Reset the board to a clean state.
    def reset(self) -> LoggedExchange:
        return self.call({"action": "reset"})

    # Fetch the clean map layout.
    def get_map(self) -> LoggedExchange:
        return self.call({"action": "getMap"})

    # Fetch Hub action costs for reporting and budget checks.
    def action_cost(self) -> LoggedExchange:
        return self.call({"action": "actionCost"})

    # Return all known units.
    def get_objects(self) -> LoggedExchange:
        return self.call({"action": "getObjects"})

    # Return inspection logs.
    def get_logs(self) -> LoggedExchange:
        return self.call({"action": "getLogs"})

    # Return action point spending.
    def expenses(self) -> LoggedExchange:
        return self.call({"action": "expenses"})

    # Create a transporter with a bounded passenger count.
    def create_transporter(self, passengers: int) -> LoggedExchange:
        if not 1 <= passengers <= 4:
            raise ValueError("transporter passengers must be between 1 and 4.")
        return self.call(
            {
                "action": "create",
                "type": "transporter",
                "passengers": passengers,
            }
        )

    # Move one object hash to one Hub coordinate.
    def move(self, object_id: str, where: str) -> LoggedExchange:
        return self.call({"action": "move", "object": object_id, "where": where})

    # Dismount scouts from one transporter.
    def dismount(self, object_id: str, passengers: int) -> LoggedExchange:
        return self.call(
            {
                "action": "dismount",
                "object": object_id,
                "passengers": passengers,
            }
        )

    # Inspect the current field of one scout.
    def inspect(self, object_id: str) -> LoggedExchange:
        return self.call({"action": "inspect", "object": object_id})

    # Call the helicopter to a confirmed survivor location.
    def call_helicopter(self, destination: str) -> LoggedExchange:
        return self.call(
            {"action": "callHelicopter", "destination": destination}
        )
