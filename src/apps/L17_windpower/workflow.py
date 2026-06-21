# Timed orchestration for the L17 windpower workflow.

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Protocol

from src.apps.L17_windpower.api_client import WindpowerApiClient
from src.apps.L17_windpower.config import AppConfig, ensure_runtime_directories
from src.apps.L17_windpower.models import (
    ApiResponse,
    ConfigPoint,
    LoggedExchange,
    SignedConfigPoint,
    WorkflowResult,
)
from src.apps.L17_windpower.run_log import RunLog, append_event, create_run_log
from src.apps.L17_windpower.solver import (
    parse_documentation,
    parse_powerplant_report,
    parse_turbine_report,
    parse_weather,
    solve_schedule,
)


REDACTED_FLAG_MARKER = "***REDACTED_FLAG***"
FLAG_PREFIX = "".join(chr(value) for value in (70, 76, 71))
FLAG_PATTERN = re.compile(r"\{" + FLAG_PREFIX + r":[^}]+\}")


# Define the Hub client behavior needed by the workflow and tests.
class WindpowerClientProtocol(Protocol):
    # Request direct documentation or queue one report.
    def get(self, param: str) -> LoggedExchange:
        ...

    # Start the timed service window.
    def start(self) -> LoggedExchange:
        ...

    # Fetch one queued result if available.
    def get_result(self) -> LoggedExchange:
        ...

    # Queue unlock-code generation for one config point.
    def unlock_code_generator(self, point: ConfigPoint) -> LoggedExchange:
        ...

    # Submit the batch config.
    def config(self, configs: dict[str, dict[str, Any]]) -> LoggedExchange:
        ...

    # Validate the final configuration.
    def done(self) -> LoggedExchange:
        ...

    # Return the number of real or fake requests used.
    def request_count(self) -> int:
        ...


# Build the live HTTP client from app config.
def build_live_client(config: AppConfig) -> WindpowerApiClient:
    if config.hub is None:
        raise ValueError("Hub config is required for the live windpower workflow.")
    return WindpowerApiClient(
        config.hub,
        timeout_seconds=config.runtime.request_timeout_seconds,
        max_requests=config.runtime.max_hub_requests,
    )


# Return whether one response contains a FLAG anywhere in its visible content.
def response_contains_flag(response: ApiResponse) -> bool:
    haystack = response.text
    if response.payload is not None:
        haystack = f"{haystack}\n{json.dumps(response.payload, ensure_ascii=False)}"
    return REDACTED_FLAG_MARKER in haystack or FLAG_PATTERN.search(haystack) is not None


# Raise a useful error when the Hub returns a non-dict payload.
def require_payload(exchange: LoggedExchange, *, action: str) -> dict[str, Any]:
    payload = exchange.response.payload
    if not isinstance(payload, dict):
        raise ValueError(f"{action} returned a non-JSON-object payload.")
    return payload


# Return whether a payload looks like the direct turbine documentation response.
def is_documentation_payload(payload: dict[str, Any]) -> bool:
    return "ratedPowerKw" in payload and "safety" in payload


# Log one exchange without allowing request secrets to reach disk.
def log_exchange(
    run_log: RunLog,
    *,
    event: str,
    exchange: LoggedExchange,
    secret_values: list[str],
) -> None:
    append_event(
        run_log,
        event=event,
        data={
            "request": exchange.request,
            "response": {
                "status_code": exchange.response.status_code,
                "payload": exchange.response.payload,
                "text": exchange.response.text,
                "flag_found": response_contains_flag(exchange.response),
            },
        },
        secret_values=secret_values,
    )


# Build a stable matching key for unlock-code requests and responses.
def unlock_key(
    *,
    start_date: str,
    start_hour: str,
    wind_ms: Any,
    pitch_angle: Any,
) -> tuple[str, str, float, float]:
    return (
        str(start_date),
        str(start_hour),
        round(float(wind_ms), 3),
        round(float(pitch_angle), 3),
    )


# Return the unlock matching key for one config point.
def unlock_key_for_point(point: ConfigPoint) -> tuple[str, str, float, float]:
    return unlock_key(
        start_date=point.start_date,
        start_hour=point.start_hour,
        wind_ms=point.wind_ms,
        pitch_angle=point.pitch_angle,
    )


# Return the unlock matching key from one generator result.
def unlock_key_from_result(payload: dict[str, Any]) -> tuple[str, str, float, float]:
    signed = payload.get("signedParams")
    if not isinstance(signed, dict):
        raise ValueError("unlockCodeGenerator result is missing signedParams.")
    return unlock_key(
        start_date=signed["startDate"],
        start_hour=signed["startHour"],
        wind_ms=signed["windMs"],
        pitch_angle=signed["pitchAngle"],
    )


# Poll the shared result queue until every requested source has been collected.
def collect_sources(
    client: WindpowerClientProtocol,
    run_log: RunLog,
    *,
    expected_sources: set[str],
    deadline: float,
    poll_interval_seconds: float,
    secret_values: list[str],
) -> dict[str, dict[str, Any]]:
    collected: dict[str, dict[str, Any]] = {}
    while expected_sources - set(collected):
        if time.monotonic() >= deadline:
            missing = sorted(expected_sources - set(collected))
            raise TimeoutError(f"Timed out waiting for queued sources: {missing}.")

        exchange = client.get_result()
        log_exchange(
            run_log,
            event="get_result",
            exchange=exchange,
            secret_values=secret_values,
        )
        payload = require_payload(exchange, action="getResult")
        source = payload.get("sourceFunction")
        if isinstance(source, str) and source in expected_sources:
            collected[source] = payload
            continue
        time.sleep(poll_interval_seconds)
    return collected


# Poll the shared result queue until every unlock code has been collected.
def collect_unlock_codes(
    client: WindpowerClientProtocol,
    run_log: RunLog,
    *,
    points: list[ConfigPoint],
    deadline: float,
    poll_interval_seconds: float,
    secret_values: list[str],
) -> list[SignedConfigPoint]:
    pending = {unlock_key_for_point(point): point for point in points}
    signed_points: dict[tuple[str, str, float, float], SignedConfigPoint] = {}

    while set(pending) - set(signed_points):
        if time.monotonic() >= deadline:
            missing = sorted(set(pending) - set(signed_points))
            raise TimeoutError(f"Timed out waiting for unlock codes: {missing}.")

        exchange = client.get_result()
        log_exchange(
            run_log,
            event="get_result_unlock",
            exchange=exchange,
            secret_values=secret_values,
        )
        payload = require_payload(exchange, action="getResult")
        if payload.get("sourceFunction") != "unlockCodeGenerator":
            time.sleep(poll_interval_seconds)
            continue

        key = unlock_key_from_result(payload)
        if key not in pending:
            raise ValueError(f"Unexpected unlockCodeGenerator result for {key}.")
        unlock_code = str(payload.get("unlockCode", "")).strip()
        if not unlock_code:
            raise ValueError("unlockCodeGenerator result is missing unlockCode.")
        signed_points[key] = SignedConfigPoint(point=pending[key], unlock_code=unlock_code)

    return [signed_points[key] for key in pending]


# Build the batch config payload accepted by the Hub.
def build_batch_configs(signed_points: list[SignedConfigPoint]) -> dict[str, dict[str, Any]]:
    configs: dict[str, dict[str, Any]] = {}
    for signed in signed_points:
        point = signed.point
        configs[point.timestamp] = {
            "pitchAngle": point.pitch_angle,
            "turbineMode": point.turbine_mode,
            "unlockCode": signed.unlock_code,
        }
    return configs


# Write one JSON artifact under the run output directory.
def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


# Run the full timed windpower workflow.
def run_windpower_workflow(
    config: AppConfig,
    *,
    client: WindpowerClientProtocol | None = None,
) -> WorkflowResult:
    ensure_runtime_directories(config.paths)
    run_log = create_run_log(config.paths.logs_dir)
    active_client = client or build_live_client(config)
    secret_values = [config.hub.api_key] if config.hub else []

    documentation_exchange = active_client.get("documentation")
    log_exchange(
        run_log,
        event="documentation",
        exchange=documentation_exchange,
        secret_values=secret_values,
    )
    documentation_payload = require_payload(documentation_exchange, action="documentation")
    start_exchange: LoggedExchange | None = None
    if not is_documentation_payload(documentation_payload):
        start_exchange = active_client.start()
        log_exchange(run_log, event="start", exchange=start_exchange, secret_values=secret_values)
        documentation_exchange = active_client.get("documentation")
        log_exchange(
            run_log,
            event="documentation_after_start",
            exchange=documentation_exchange,
            secret_values=secret_values,
        )
        documentation_payload = require_payload(documentation_exchange, action="documentation")

    documentation = parse_documentation(documentation_payload)

    if start_exchange is None:
        start_exchange = active_client.start()
        log_exchange(run_log, event="start", exchange=start_exchange, secret_values=secret_values)
    deadline = time.monotonic() + config.runtime.local_deadline_seconds

    for report_name in ("weather", "turbinecheck", "powerplantcheck"):
        exchange = active_client.get(report_name)
        log_exchange(
            run_log,
            event=f"queue_{report_name}",
            exchange=exchange,
            secret_values=secret_values,
        )

    reports = collect_sources(
        active_client,
        run_log,
        expected_sources={"weather", "turbinecheck", "powerplantcheck"},
        deadline=deadline,
        poll_interval_seconds=config.runtime.poll_interval_seconds,
        secret_values=secret_values,
    )

    weather = parse_weather(reports["weather"])
    turbine = parse_turbine_report(reports["turbinecheck"])
    powerplant = parse_powerplant_report(reports["powerplantcheck"])
    points = solve_schedule(
        documentation=documentation,
        weather=weather,
        turbine=turbine,
        powerplant=powerplant,
    )
    append_event(
        run_log,
        event="schedule_solved",
        data={
            "points": [
                {
                    "timestamp": point.timestamp,
                    "wind_ms": point.wind_ms,
                    "pitch_angle": point.pitch_angle,
                    "turbine_mode": point.turbine_mode,
                    "reason": point.reason,
                }
                for point in points
            ]
        },
        secret_values=secret_values,
    )

    for point in points:
        exchange = active_client.unlock_code_generator(point)
        log_exchange(
            run_log,
            event="queue_unlock_code",
            exchange=exchange,
            secret_values=secret_values,
        )

    signed_points = collect_unlock_codes(
        active_client,
        run_log,
        points=points,
        deadline=deadline,
        poll_interval_seconds=config.runtime.poll_interval_seconds,
        secret_values=secret_values,
    )
    configs = build_batch_configs(signed_points)

    config_exchange = active_client.config(configs)
    log_exchange(run_log, event="config", exchange=config_exchange, secret_values=secret_values)

    done_exchange = active_client.done()
    log_exchange(run_log, event="done", exchange=done_exchange, secret_values=secret_values)

    final_response_path = config.paths.output_dir / f"final_response_{run_log.run_id}.json"
    write_json(
        final_response_path,
        {
            "status_code": done_exchange.response.status_code,
            "payload": done_exchange.response.payload,
            "text": done_exchange.response.text,
            "flag_found": response_contains_flag(done_exchange.response),
        },
    )

    run_report_path = config.paths.output_dir / f"run_report_{run_log.run_id}.json"
    write_json(
        run_report_path,
        {
            "status": "solved" if response_contains_flag(done_exchange.response) else "completed",
            "run_id": run_log.run_id,
            "request_count": active_client.request_count(),
            "config_count": len(configs),
            "config_timestamps": sorted(configs),
            "run_log_path": str(run_log.path.relative_to(config.paths.repo_root)),
            "final_response_path": str(final_response_path.relative_to(config.paths.repo_root)),
            "flag_found": response_contains_flag(done_exchange.response),
        },
    )

    return WorkflowResult(
        status="solved" if response_contains_flag(done_exchange.response) else "completed",
        run_log_path=str(run_log.path.relative_to(config.paths.repo_root)),
        run_report_path=str(run_report_path.relative_to(config.paths.repo_root)),
        final_response_path=str(final_response_path.relative_to(config.paths.repo_root)),
        config_count=len(configs),
        flag_found=response_contains_flag(done_exchange.response),
    )
