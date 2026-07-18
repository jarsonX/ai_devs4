# SQLite coordination blackboard for the L25 supervisor and agents.

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from src.apps.L25_timetravel.models import AgentRole, Phase


SCHEMA_VERSION = 1


# Return one stable UTC timestamp for persisted coordination records.
def utc_now() -> datetime:
    return datetime.now(UTC)


# Serialize JSON payloads consistently without leaking object representations.
def encode_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


# Own the single-process SQLite database and atomic workflow transitions.
class CoordinationStore:
    # Open one short-transaction connection and initialize the schema.
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.connection = sqlite3.connect(path, timeout=5.0)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self._initialize_schema()

    # Close the connection explicitly at application shutdown.
    def close(self) -> None:
        self.connection.close()

    # Create all coordination tables without changing existing run data.
    def _initialize_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                phase TEXT NOT NULL,
                status TEXT NOT NULL,
                state_version INTEGER NOT NULL,
                frozen_current_date TEXT,
                active_leg INTEGER,
                activation_attempts INTEGER NOT NULL DEFAULT 0,
                flag_found INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS commands (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES runs(id),
                role TEXT NOT NULL,
                kind TEXT NOT NULL,
                state_version INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                claimed_at TEXT,
                completed_at TEXT,
                result_json TEXT,
                UNIQUE(run_id, idempotency_key)
            );
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL REFERENCES runs(id),
                role TEXT NOT NULL,
                kind TEXT NOT NULL,
                state_version INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                evidence_path TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS activation_leases (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES runs(id),
                state_version INTEGER NOT NULL,
                config_digest TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                consumed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL REFERENCES runs(id),
                role TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS agent_status (
                run_id TEXT NOT NULL REFERENCES runs(id),
                role TEXT NOT NULL,
                status TEXT NOT NULL,
                current_command_id TEXT,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                heartbeat_at TEXT NOT NULL,
                PRIMARY KEY(run_id, role)
            );
            """
        )
        self.connection.execute(
            "INSERT OR REPLACE INTO schema_meta(key, value) VALUES('version', ?)",
            (str(SCHEMA_VERSION),),
        )
        self.connection.commit()

    # Run one immediate transaction so a claim or transition cannot interleave.
    @contextmanager
    def immediate(self) -> Iterator[sqlite3.Connection]:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield self.connection
        except Exception:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    # Create one new workflow run with no external side effects.
    def create_run(self, run_id: str | None = None) -> str:
        identifier = run_id or uuid.uuid4().hex
        now = utc_now().isoformat()
        with self.immediate() as connection:
            connection.execute(
                """
                INSERT INTO runs(
                    id, phase, status, state_version, created_at, updated_at
                ) VALUES(?, ?, 'running', 1, ?, ?)
                """,
                (identifier, Phase.BOOTSTRAP.value, now, now),
            )
            for role in AgentRole:
                connection.execute(
                    """
                    INSERT INTO agent_status(
                        run_id, role, status, heartbeat_at
                    ) VALUES(?, ?, 'idle', ?)
                    """,
                    (identifier, role.value, now),
                )
        return identifier

    # Return one run as a plain dictionary for validated higher-level parsing.
    def get_run(self, run_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT * FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"Run {run_id!r} does not exist.")
        return dict(row)

    # Advance one run only from the caller's expected state version.
    def transition_run(
        self,
        run_id: str,
        expected_version: int,
        phase: Phase,
        *,
        status: str = "running",
        frozen_current_date: str | None = None,
        active_leg: int | None = None,
        flag_found: bool | None = None,
        last_error: str | None = None,
    ) -> int:
        now = utc_now().isoformat()
        with self.immediate() as connection:
            current = connection.execute(
                "SELECT * FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
            if current is None:
                raise KeyError(f"Run {run_id!r} does not exist.")
            if current["state_version"] != expected_version:
                raise RuntimeError("Run state version is stale.")
            next_version = expected_version + 1
            connection.execute(
                """
                UPDATE runs SET
                    phase = ?, status = ?, state_version = ?,
                    frozen_current_date = COALESCE(?, frozen_current_date),
                    active_leg = COALESCE(?, active_leg),
                    flag_found = COALESCE(?, flag_found),
                    last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    phase.value,
                    status,
                    next_version,
                    frozen_current_date,
                    active_leg,
                    int(flag_found) if flag_found is not None else None,
                    last_error,
                    now,
                    run_id,
                ),
            )
        return next_version

    # Persist one immutable typed observation for later reconciliation.
    def append_observation(
        self,
        run_id: str,
        role: AgentRole,
        kind: str,
        state_version: int,
        payload: dict[str, Any],
        evidence_path: str | None = None,
    ) -> int:
        cursor = self.connection.execute(
            """
            INSERT INTO observations(
                run_id, role, kind, state_version, payload_json,
                evidence_path, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                role.value,
                kind,
                state_version,
                encode_json(payload),
                evidence_path,
                utc_now().isoformat(),
            ),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    # Return the newest observation of one kind for one role and version.
    def latest_observation(
        self,
        run_id: str,
        role: AgentRole,
        kind: str,
        state_version: int,
    ) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT * FROM observations
            WHERE run_id = ? AND role = ? AND kind = ? AND state_version = ?
            ORDER BY id DESC LIMIT 1
            """,
            (run_id, role.value, kind, state_version),
        ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["payload"] = json.loads(result.pop("payload_json"))
        return result

    # Create one idempotent expiring command for exactly one agent role.
    def create_command(
        self,
        run_id: str,
        role: AgentRole,
        kind: str,
        state_version: int,
        payload: dict[str, Any],
        idempotency_key: str,
        expires_at: datetime,
    ) -> str:
        identifier = uuid.uuid4().hex
        with self.immediate() as connection:
            existing = connection.execute(
                """
                SELECT id FROM commands
                WHERE run_id = ? AND idempotency_key = ?
                """,
                (run_id, idempotency_key),
            ).fetchone()
            if existing is not None:
                return str(existing["id"])
            connection.execute(
                """
                INSERT INTO commands(
                    id, run_id, role, kind, state_version, payload_json,
                    status, idempotency_key, expires_at
                ) VALUES(?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    identifier,
                    run_id,
                    role.value,
                    kind,
                    state_version,
                    encode_json(payload),
                    idempotency_key,
                    expires_at.isoformat(),
                ),
            )
        return identifier

    # Atomically claim the oldest unexpired command assigned to one role.
    def claim_command(self, run_id: str, role: AgentRole) -> dict[str, Any] | None:
        now = utc_now()
        with self.immediate() as connection:
            row = connection.execute(
                """
                SELECT * FROM commands
                WHERE run_id = ? AND role = ? AND status = 'pending'
                ORDER BY rowid ASC LIMIT 1
                """,
                (run_id, role.value),
            ).fetchone()
            if row is None:
                return None
            if datetime.fromisoformat(row["expires_at"]) <= now:
                connection.execute(
                    "UPDATE commands SET status = 'expired' WHERE id = ?",
                    (row["id"],),
                )
                return None
            connection.execute(
                """
                UPDATE commands SET status = 'claimed', claimed_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (now.isoformat(), row["id"]),
            )
            result = dict(row)
            result["payload"] = json.loads(result.pop("payload_json"))
            result["status"] = "claimed"
            return result

    # Finish one claimed command with a secret-safe result payload.
    def complete_command(
        self,
        command_id: str,
        status: str,
        result: dict[str, Any],
    ) -> None:
        if status not in {"completed", "failed", "blocked"}:
            raise ValueError("Unsupported terminal command status.")
        with self.immediate() as connection:
            row = connection.execute(
                "SELECT status FROM commands WHERE id = ?", (command_id,)
            ).fetchone()
            if row is None or row["status"] != "claimed":
                raise RuntimeError("Command is not in claimed state.")
            connection.execute(
                """
                UPDATE commands SET status = ?, result_json = ?, completed_at = ?
                WHERE id = ?
                """,
                (status, encode_json(result), utc_now().isoformat(), command_id),
            )

    # Create one short activation lease bound to a state version and digest.
    def issue_activation_lease(
        self,
        run_id: str,
        state_version: int,
        config_digest: str,
        expires_at: datetime,
    ) -> str:
        identifier = uuid.uuid4().hex
        self.connection.execute(
            """
            INSERT INTO activation_leases(
                id, run_id, state_version, config_digest, expires_at
            ) VALUES(?, ?, ?, ?, ?)
            """,
            (identifier, run_id, state_version, config_digest, expires_at.isoformat()),
        )
        self.connection.commit()
        return identifier

    # Consume one valid lease exactly once or fail before a browser click.
    def consume_activation_lease(
        self,
        lease_id: str,
        run_id: str,
        state_version: int,
        config_digest: str,
    ) -> None:
        now = utc_now()
        with self.immediate() as connection:
            row = connection.execute(
                "SELECT * FROM activation_leases WHERE id = ?", (lease_id,)
            ).fetchone()
            if row is None:
                raise RuntimeError("Activation lease does not exist.")
            if row["run_id"] != run_id or row["state_version"] != state_version:
                raise RuntimeError("Activation lease state does not match.")
            if row["config_digest"] != config_digest:
                raise RuntimeError("Activation lease digest does not match.")
            if row["consumed_at"] is not None:
                raise RuntimeError("Activation lease was already consumed.")
            if datetime.fromisoformat(row["expires_at"]) <= now:
                raise RuntimeError("Activation lease has expired.")
            connection.execute(
                "UPDATE activation_leases SET consumed_at = ? WHERE id = ?",
                (now.isoformat(), lease_id),
            )

    # Append one safe audit event for debugging and final reporting.
    def append_event(
        self,
        run_id: str,
        role: AgentRole,
        event_type: str,
        payload: dict[str, Any],
    ) -> int:
        cursor = self.connection.execute(
            """
            INSERT INTO events(run_id, role, event_type, payload_json, created_at)
            VALUES(?, ?, ?, ?, ?)
            """,
            (run_id, role.value, event_type, encode_json(payload), utc_now().isoformat()),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

