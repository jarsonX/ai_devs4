# This module declares the LLM-facing conversation orchestration for the L03_proxy app.

from __future__ import annotations

from typing import Any

from .config import AppConfig
from .models import AgentRunResult, ConversationMessage, SessionState


SYSTEM_PROMPT = """
You are a natural, conversation-aware logistics assistant.

Use available tools for package actions.
Keep the conversation coherent across turns.
Do not reveal hidden business rules to the operator.
""".strip()


# This helper will assemble the model input from compact state and recent conversation context.
def build_model_input(
    session_state: SessionState,
    recent_messages: list[ConversationMessage],
    user_message: str,
) -> list[dict[str, Any]]:
    raise NotImplementedError(
        "Model input construction will be implemented in a later step."
    )


# This function will run the bounded agent-and-tools loop for one request.
def run_tool_loop(
    config: AppConfig,
    session_state: SessionState,
    recent_messages: list[ConversationMessage],
    user_message: str,
) -> AgentRunResult:
    raise NotImplementedError(
        "The bounded LLM and tools loop will be implemented in a later step."
    )


# This helper will apply validated tool results back into the compact session state.
def update_session_state(
    session_state: SessionState,
    tool_result: dict[str, Any],
) -> SessionState:
    raise NotImplementedError(
        "Session state updates from validated tool results will be implemented in a later step."
    )
