# This module defines shared request, response, session, and tool data models for the L03_proxy app.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# This helper validates one required non-empty string field from dictionary payloads.
def get_required_string(
    payload: dict[str, Any],
    key: str,
    max_length: int | None = None,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string.")

    cleaned_value = value.strip()
    if not cleaned_value:
        raise ValueError(f"{key} cannot be empty.")
    if max_length is not None and len(cleaned_value) > max_length:
        raise ValueError(f"{key} cannot be longer than {max_length} characters.")

    return cleaned_value


# This helper reads a string field and falls back to an empty string for invalid values.
def get_optional_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    return value if isinstance(value, str) else ""


# This helper reads an optional string field and falls back to None for invalid values.
def get_optional_nullable_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) else None


# This helper reads a boolean field and falls back to False for invalid values.
def get_optional_bool(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    return value if isinstance(value, bool) else False


# This helper reads a dictionary field and falls back to an empty dictionary for invalid values.
def get_optional_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


# This model represents the normalized HTTP request handled by the app.
@dataclass(frozen=True)
class ProxyRequest:
    session_id: str
    msg: str

    @classmethod
    # This helper converts a raw request payload into the internal request model.
    def from_dict(
        cls,
        payload: dict[str, Any],
        max_session_id_length: int | None = None,
        max_msg_length: int | None = None,
    ) -> "ProxyRequest":
        return cls(
            session_id=get_required_string(
                payload,
                "sessionID",
                max_session_id_length,
            ),
            msg=get_required_string(payload, "msg", max_msg_length),
        )

    # This helper converts the internal request model back into API field names.
    def to_dict(self) -> dict[str, str]:
        return {
            "sessionID": self.session_id,
            "msg": self.msg,
        }


# This model represents the HTTP response returned to the operator.
@dataclass(frozen=True)
class ProxyResponse:
    msg: str

    # This helper converts the response model into the public JSON payload shape.
    def to_dict(self) -> dict[str, str]:
        return {"msg": self.msg}


# This model stores one message from the conversation transcript.
@dataclass(frozen=True)
class ConversationMessage:
    role: str
    content: str
    tool_name: str | None = None

    # This helper serializes one conversation message for storage or transport.
    def to_dict(self) -> dict[str, str]:
        payload = {
            "role": self.role,
            "content": self.content,
        }
        if self.tool_name is not None:
            payload["tool_name"] = self.tool_name

        return payload

    @classmethod
    # This helper rebuilds one conversation message from stored dictionary data.
    def from_dict(cls, payload: dict[str, Any]) -> "ConversationMessage":
        return cls(
            role=get_optional_string(payload, "role"),
            content=get_optional_string(payload, "content"),
            tool_name=get_optional_nullable_string(payload, "tool_name"),
        )


# This model keeps the compact business state remembered across requests.
@dataclass(frozen=True)
class SessionState:
    known_package_id: str | None = None
    known_security_code: str | None = None
    last_requested_destination: str | None = None
    redirect_confirmation: str | None = None
    redirect_completed: bool = False
    reactor_related_context_detected: bool = False
    last_check_result: dict[str, Any] = field(default_factory=dict)

    # This helper serializes the compact session state for persistence.
    def to_dict(self) -> dict[str, Any]:
        return {
            "known_package_id": self.known_package_id,
            "known_security_code": self.known_security_code,
            "last_requested_destination": self.last_requested_destination,
            "redirect_confirmation": self.redirect_confirmation,
            "redirect_completed": self.redirect_completed,
            "reactor_related_context_detected": self.reactor_related_context_detected,
            "last_check_result": dict(self.last_check_result),
        }

    @classmethod
    # This helper rebuilds the compact session state from stored dictionary data.
    def from_dict(cls, payload: dict[str, Any]) -> "SessionState":
        return cls(
            known_package_id=get_optional_nullable_string(payload, "known_package_id"),
            known_security_code=get_optional_nullable_string(
                payload,
                "known_security_code",
            ),
            last_requested_destination=get_optional_nullable_string(
                payload,
                "last_requested_destination",
            ),
            redirect_confirmation=get_optional_nullable_string(
                payload,
                "redirect_confirmation",
            ),
            redirect_completed=get_optional_bool(payload, "redirect_completed"),
            reactor_related_context_detected=get_optional_bool(
                payload,
                "reactor_related_context_detected",
            ),
            last_check_result=get_optional_dict(payload, "last_check_result"),
        )


# This model groups the full transcript and compact state for one session.
@dataclass(frozen=True)
class SessionData:
    session_id: str
    state: SessionState = field(default_factory=SessionState)
    messages: list[ConversationMessage] = field(default_factory=list)

    # This helper serializes the full session payload for JSON storage.
    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state": self.state.to_dict(),
            "messages": [message.to_dict() for message in self.messages],
        }

    @classmethod
    # This helper rebuilds the full session payload from stored dictionary data.
    def from_dict(cls, payload: dict[str, Any]) -> "SessionData":
        state_payload = payload.get("state")
        messages_payload = payload.get("messages")

        return cls(
            session_id=get_optional_string(payload, "session_id"),
            state=SessionState.from_dict(state_payload)
            if isinstance(state_payload, dict)
            else SessionState(),
            messages=[
                ConversationMessage.from_dict(item)
                for item in messages_payload
                if isinstance(item, dict)
            ]
            if isinstance(messages_payload, list)
            else [],
        )


# This model captures the normalized result of one tool execution.
@dataclass(frozen=True)
class ToolExecutionResult:
    tool_name: str
    ok: bool
    payload: dict[str, Any] = field(default_factory=dict)

    # This helper serializes a tool result for logging or agent state updates.
    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "ok": self.ok,
            "payload": dict(self.payload),
        }


# This model captures the final result returned by the agent for one request.
@dataclass(frozen=True)
class AgentRunResult:
    assistant_message: str
    updated_state: SessionState
    tool_results: list[ToolExecutionResult] = field(default_factory=list)
