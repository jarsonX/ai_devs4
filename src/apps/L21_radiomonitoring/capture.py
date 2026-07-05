# Listening-session capture and raw signal persistence.

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.apps.L21_radiomonitoring.config import AppConfig
from src.apps.L21_radiomonitoring.models import (
    CapturedSignal,
    LoggedExchange,
    summarize_signal_payload,
)
from src.apps.L21_radiomonitoring.verify_client import RadiomonitoringVerifyClient


# Write JSON with stable formatting for local learning artifacts.
def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# Convert a sequence of exchanges into runtime JSON data.
def exchanges_to_dict(exchanges: list[LoggedExchange]) -> list[dict[str, Any]]:
    return [exchange.to_dict() for exchange in exchanges]


# Classify one Hub payload into the local signal kind vocabulary.
def classify_signal_payload(payload: dict[str, Any], *, action: str) -> str:
    if action == "start":
        return "control"
    if "transcription" in payload:
        return "transcription"
    if "attachment" in payload:
        return "attachment"
    return "other"


# Return whether a listen response indicates that capture can stop.
def should_stop_listening(payload: dict[str, Any]) -> bool:
    if payload.get("code") == 100:
        return False
    message = str(payload.get("message", "")).lower()
    stop_markers = ("enough", "wystar", "koniec", "complete", "done", "gotowe")
    return any(marker in message for marker in stop_markers) or payload.get("code") not in {100, 110}


# Persist one raw exchange and return a signal descriptor.
def persist_signal(
    config: AppConfig,
    exchange: LoggedExchange,
    *,
    action: str,
) -> CapturedSignal:
    payload = exchange.response.payload if isinstance(exchange.response.payload, dict) else {}
    kind = classify_signal_payload(payload, action=action)
    raw_file = config.paths.raw_signals_dir / f"{exchange.sequence:03d}_{action}.json"
    write_json(
        raw_file,
        {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "exchange": exchange.to_dict(),
            "summary": summarize_signal_payload(payload),
        },
    )
    return CapturedSignal(
        sequence=exchange.sequence,
        kind=kind,  # type: ignore[arg-type]
        action=action,
        payload=payload,
        raw_file=str(raw_file.relative_to(config.paths.repo_root)),
    )


# Run a bounded listening session and preserve raw Hub exchanges.
def capture_signals(
    config: AppConfig,
    client: RadiomonitoringVerifyClient,
) -> tuple[list[CapturedSignal], list[LoggedExchange]]:
    signals: list[CapturedSignal] = []
    exchanges: list[LoggedExchange] = []

    start_exchange = client.start()
    exchanges.append(start_exchange)
    signals.append(persist_signal(config, start_exchange, action="start"))

    for _ in range(config.runtime.max_listen_requests):
        listen_exchange = client.listen()
        exchanges.append(listen_exchange)
        signal = persist_signal(config, listen_exchange, action="listen")
        signals.append(signal)
        payload = listen_exchange.response.payload
        if isinstance(payload, dict) and should_stop_listening(payload):
            break

    return signals, exchanges


# Load captured signals from raw signal cache files.
def load_cached_signals(config: AppConfig) -> list[CapturedSignal]:
    signals: list[CapturedSignal] = []
    for path in sorted(config.paths.raw_signals_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        exchange_payload = payload.get("exchange", {}).get("response", {}).get("payload", {})
        action = str(payload.get("exchange", {}).get("action", "listen"))
        sequence = int(payload.get("exchange", {}).get("sequence", 0))
        if not isinstance(exchange_payload, dict):
            continue
        signals.append(
            CapturedSignal(
                sequence=sequence,
                kind=classify_signal_payload(exchange_payload, action=action),  # type: ignore[arg-type]
                action=action,
                payload=exchange_payload,
                raw_file=str(path.relative_to(config.paths.repo_root)),
            )
        )
    return signals
