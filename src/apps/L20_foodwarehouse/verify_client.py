# Guarded HTTP client for the L20 foodwarehouse Hub API.

from __future__ import annotations

from typing import Any, Protocol

import requests

from src.apps.L20_foodwarehouse.config import HubConfig
from src.apps.L20_foodwarehouse.models import ApiResponse, LoggedExchange


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


# Send foodwarehouse task actions through one guarded HTTP session.
class FoodwarehouseVerifyClient:
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

    # Send one answer object to the Hub.
    def call(self, answer: dict[str, Any], *, action: str) -> LoggedExchange:
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

    # Ask the Hub for the task-specific tool contract.
    def help(self) -> LoggedExchange:
        return self.call({"tool": "help"}, action="help")

    # Reset remote orders to the exercise initial state.
    def reset(self) -> LoggedExchange:
        return self.call({"tool": "reset"}, action="reset")

    # Run one read-only SQLite query through the task API.
    def database_query(self, query: str) -> LoggedExchange:
        return self.call(
            {"tool": "database", "query": query},
            action=f"database:{query}",
        )

    # Ask the task signature tool to produce a SHA1 signature.
    def signature(self, payload: dict[str, Any]) -> LoggedExchange:
        answer = {"tool": "signatureGenerator", **payload}
        return self.call(answer, action="signatureGenerator")

    # Fetch the current remote orders for diagnostics.
    def orders_get(self) -> LoggedExchange:
        return self.call({"tool": "orders", "action": "get"}, action="orders:get")

    # Create one remote order header.
    def orders_create(
        self,
        *,
        title: str,
        creator_id: int,
        destination: str,
        signature: str,
    ) -> LoggedExchange:
        return self.call(
            {
                "tool": "orders",
                "action": "create",
                "title": title,
                "creatorID": creator_id,
                "destination": destination,
                "signature": signature,
            },
            action=f"orders:create:{title}",
        )

    # Append all demanded items to one order in batch mode.
    def orders_append(self, *, order_id: str, items: dict[str, int]) -> LoggedExchange:
        return self.call(
            {
                "tool": "orders",
                "action": "append",
                "id": order_id,
                "items": items,
            },
            action=f"orders:append:{order_id}",
        )

    # Ask the Hub to validate the finished order set.
    def done(self) -> LoggedExchange:
        return self.call({"tool": "done"}, action="done")
