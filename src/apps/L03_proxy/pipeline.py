# This module defines the high-level request pipeline for the L03_proxy app.

from __future__ import annotations

from dataclasses import replace
from typing import Any

from .agent import run_tool_loop
from .config import AppConfig, ensure_runtime_directories, get_config
from .models import ConversationMessage, ProxyRequest, ProxyResponse, SessionData
from .session_store import load_session, save_session


# This helper selects the recent conversation window sent to the agent.
def select_recent_messages(
    session_data: SessionData,
    message_limit: int,
) -> list[ConversationMessage]:
    if message_limit <= 0:
        return []

    return session_data.messages[-message_limit:]


# This helper appends the current user turn and assistant reply to the transcript.
def append_conversation_turn(
    session_data: SessionData,
    user_message: str,
    assistant_message: str,
) -> list[ConversationMessage]:
    return [
        *session_data.messages,
        ConversationMessage(role="user", content=user_message),
        ConversationMessage(role="assistant", content=assistant_message),
    ]


# This function handles one validated proxy request from intake to persisted response.
def handle_request(
    payload: dict[str, Any],
    config: AppConfig | None = None,
) -> dict[str, str]:
    runtime_config = config or get_config()
    ensure_runtime_directories(runtime_config)

    request = ProxyRequest.from_dict(payload)
    session_data = load_session(runtime_config, request.session_id)
    recent_messages = select_recent_messages(
        session_data,
        runtime_config.recent_message_limit,
    )

    agent_result = run_tool_loop(
        config=runtime_config,
        session_state=session_data.state,
        recent_messages=recent_messages,
        user_message=request.msg,
    )
    updated_messages = append_conversation_turn(
        session_data,
        request.msg,
        agent_result.assistant_message,
    )
    updated_session = replace(
        session_data,
        state=agent_result.updated_state,
        messages=updated_messages,
    )
    save_session(runtime_config, updated_session)

    return ProxyResponse(msg=agent_result.assistant_message).to_dict()
