# Guarded Hub API boundary for L25 timetravel.

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import requests

from src.apps.L25_timetravel.config import HubConfig, RuntimeConfig
from src.apps.L25_timetravel.models import HubResult, MachineSnapshot


SUCCESS_CODES = {"help": 14, "getConfig": 12, "configure": 11}
EDITABLE_PARAMS = frozenset({"day", "month", "year", "syncRatio", "stabilization"})


# Preserve a validated Hub failure without exposing the API key.
class HubError(RuntimeError):
    # Store safe status and domain metadata for recovery decisions.
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


# Bound total Hub traffic before any logical request is sent.
class HubRequestGuard:
    # Store the maximum and consumed logical requests.
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.used = 0

    # Consume one slot or fail before network traffic.
    def consume(self) -> None:
        if self.used >= self.limit:
            raise RuntimeError(f"Hub request guard reached {self.limit} calls.")
        self.used += 1


# Send only typed timetravel actions and retain secret-safe exchange metadata.
class TimetravelHubClient:
    # Store configuration, injectable session, and strict request guard.
    def __init__(
        self,
        config: HubConfig,
        runtime: RuntimeConfig,
        *,
        session: requests.Session | Any | None = None,
        guard: HubRequestGuard | None = None,
    ) -> None:
        self.config = config
        self.runtime = runtime
        self.session = session or requests.Session()
        self.guard = guard or HubRequestGuard(runtime.max_hub_requests)
        self._exchanges: list[dict[str, Any]] = []

    # Return how many logical Hub requests were attempted.
    def request_count(self) -> int:
        return self.guard.used

    # Return secret-safe request and response metadata for runtime reports.
    def exchanges(self) -> list[dict[str, Any]]:
        return list(self._exchanges)

    # Request and validate one Hub action.
    def _request(self, answer: dict[str, Any], expected_action: str) -> HubResult:
        self.guard.consume()
        response = self.session.post(
            self.config.verify_url,
            json={
                "apikey": self.config.api_key,
                "task": self.config.task_name,
                "answer": answer,
            },
            timeout=self.runtime.request_timeout_seconds,
        )
        try:
            payload = response.json()
        except Exception as error:
            self._record(expected_action, response.status_code, None, "invalid_json")
            raise HubError(
                "Hub returned invalid JSON.", status_code=response.status_code
            ) from error
        code = payload.get("code") if isinstance(payload, dict) else None
        message = payload.get("message") if isinstance(payload, dict) else None
        self._record(expected_action, response.status_code, code, message)
        if not isinstance(payload, dict):
            raise HubError("Hub payload is not an object.", status_code=response.status_code)
        expected_code = SUCCESS_CODES[expected_action]
        if not response.ok or code != expected_code:
            raise HubError(
                str(message or "Hub rejected the request."),
                status_code=response.status_code,
                code=code if isinstance(code, int) else None,
            )
        result = HubResult.model_validate(payload)
        if result.config is not None:
            result.config.captured_at = datetime.now(UTC)
            if result.needConfig:
                result.config.needConfig = result.needConfig
        return result

    # Preserve only safe exchange metadata without request payloads or secrets.
    def _record(
        self,
        action: str,
        status_code: int,
        code: int | None,
        message: str | None,
    ) -> None:
        self._exchanges.append(
            {
                "sequence": self.guard.used,
                "action": action,
                "status_code": status_code,
                "code": code,
                "message": str(message)[:500] if message is not None else None,
                "captured_at": datetime.now(UTC).isoformat(),
            }
        )

    # Return the documented Hub help response.
    def help(self) -> HubResult:
        return self._request({"action": "help"}, "help")

    # Return one authoritative current machine snapshot.
    def get_config(self) -> MachineSnapshot:
        result = self._request({"action": "getConfig"}, "getConfig")
        if result.config is None:
            raise HubError("getConfig returned no machine config.")
        return result.config

    # Apply one accepted backend field after confirming standby.
    def configure(self, param: str, value: int | float) -> MachineSnapshot:
        if param not in EDITABLE_PARAMS:
            raise ValueError(f"Unsupported configure parameter: {param!r}.")
        before = self.get_config()
        if before.mode != "standby":
            raise HubError("Configuration requires standby mode.")
        try:
            result = self._request(
                {"action": "configure", "param": param, "value": value},
                "configure",
            )
        except requests.RequestException:
            reconciled = self.get_config()
            if getattr(reconciled, param) == value:
                return reconciled
            raise
        if result.config is None:
            raise HubError("configure returned no machine config.")
        return result.config
