# Strict domain and agent boundary models for L25 timetravel.

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# Enumerate the only workflow phases accepted by the supervisor.
class Phase(str, Enum):
    BOOTSTRAP = "BOOTSTRAP"
    PREPARE_2238 = "PREPARE_2238"
    WAIT_MODE_3 = "WAIT_MODE_3"
    JUMP_2238 = "JUMP_2238"
    VERIFY_BATTERY_REPLACEMENT = "VERIFY_BATTERY_REPLACEMENT"
    PREPARE_RETURN = "PREPARE_RETURN"
    WAIT_MODE_2_RETURN = "WAIT_MODE_2_RETURN"
    JUMP_TO_PRESENT = "JUMP_TO_PRESENT"
    VERIFY_PRESENT = "VERIFY_PRESENT"
    PREPARE_2024_TUNNEL = "PREPARE_2024_TUNNEL"
    WAIT_MODE_2_TUNNEL = "WAIT_MODE_2_TUNNEL"
    OPEN_TUNNEL = "OPEN_TUNNEL"
    VERIFY_FLAG = "VERIFY_FLAG"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


# Enumerate the only roles that may write coordination records.
class AgentRole(str, Enum):
    SUPERVISOR = "supervisor"
    BACKEND = "backend"
    FRONTEND = "frontend"


# Enumerate one backend agent decision per bounded model step.
class BackendAction(str, Enum):
    INSPECT = "inspect"
    CONFIGURE = "configure"
    EXTRACT_STABILIZATION = "extract_stabilization"
    COMPLETE = "complete"
    BLOCKED = "blocked"


# Enumerate one frontend agent decision per bounded model step.
class FrontendAction(str, Enum):
    INSPECT = "inspect"
    SET_PORTS = "set_ports"
    SET_POWER = "set_power"
    SET_MODE = "set_mode"
    READY = "ready"
    BLOCKED = "blocked"


# Represent one fully validated calendar target.
class TargetDate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    year: int = Field(ge=1500, le=2499)
    month: int = Field(ge=1, le=12)
    day: int = Field(ge=1, le=31)

    # Reject impossible calendar dates that pass simple numeric ranges.
    @model_validator(mode="after")
    def validate_calendar_date(self) -> "TargetDate":
        date(self.year, self.month, self.day)
        return self

    # Return the ISO date used by machine snapshots and digests.
    def isoformat(self) -> str:
        return date(self.year, self.month, self.day).isoformat()


# Describe one deterministic travel leg.
class TravelLeg(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: Literal["battery_jump", "return", "tunnel"]
    target: TargetDate
    pta: bool
    ptb: bool
    pwr: int = Field(ge=0, le=100)
    required_internal_mode: int = Field(ge=1, le=4)
    sync_ratio: float = Field(ge=0, le=1)
    tunnel: bool = False


# Normalize the complete machine snapshot shared by Hub and browser checks.
class MachineSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    currentDate: str
    day: int | None = None
    month: int | None = None
    year: int | None = None
    syncRatio: float | None = None
    stabilization: int | None = None
    condition: str
    fluxDensity: int = Field(ge=0, le=100)
    batteryStatus: str
    PTA: bool
    PTB: bool
    PWR: int = Field(ge=0, le=100)
    mode: Literal["standby", "active"]
    internalMode: int = Field(ge=1, le=4)
    needConfig: str | None = None
    captured_at: datetime | None = None

    # Return the configured target only when all three fields are present.
    def target(self) -> TargetDate | None:
        if self.year is None or self.month is None or self.day is None:
            return None
        return TargetDate(year=self.year, month=self.month, day=self.day)

    # Parse the machine battery fraction into charged and total cells.
    def battery_cells(self) -> tuple[int, int]:
        charged_text, total_text = self.batteryStatus.split("/", 1)
        return int(charged_text), int(total_text)


# Combine the shared machine snapshot with frontend-only readiness signals.
class FrontendObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    machine: MachineSnapshot
    orb_powered: bool
    orb_danger: bool
    activation_ready: bool
    same_date_warning: bool
    toast: str | None = None
    flag: str | None = None


# Preserve a validated Hub response without leaking request secrets.
class HubResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: int
    message: str
    config: MachineSnapshot | None = None
    needConfig: str | None = None
    flag: str | None = None
    audio: str | None = None


# Represent arithmetic extracted from a stabilization hint.
class StabilizationExpression(BaseModel):
    model_config = ConfigDict(extra="forbid")

    left: int = Field(ge=0, le=10_000)
    operator: Literal["+", "-", "*", "/"]
    right: int = Field(ge=0, le=10_000)


# Represent one backend model action before deterministic authorization.
class BackendDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: BackendAction
    param: Literal["day", "month", "year", "syncRatio", "stabilization"] | None = None
    value: int | float | None = None
    expression: StabilizationExpression | None = None
    reason: str = Field(max_length=240)


# Represent one frontend model action before deterministic authorization.
class FrontendDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: FrontendAction
    pta: bool | None = None
    ptb: bool | None = None
    pwr: int | None = Field(default=None, ge=0, le=100)
    mode: Literal["standby", "active"] | None = None
    reason: str = Field(max_length=240)


# Describe one command persisted for exactly one role and state version.
class AgentCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    role: AgentRole
    kind: str
    state_version: int = Field(ge=1)
    payload: dict[str, Any]
    expires_at: datetime


# Describe a short-lived, one-time activation authorization.
class ActivationLease(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    run_id: str
    state_version: int = Field(ge=1)
    config_digest: str
    expires_at: datetime
    consumed_at: datetime | None = None
