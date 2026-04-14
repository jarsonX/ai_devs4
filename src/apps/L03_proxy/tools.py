# This module declares tool schemas and dispatch contracts for the L03_proxy app.

from __future__ import annotations

from typing import Any

from .config import AppConfig
from .models import SessionState, ToolExecutionResult
from .package_api_client import PackageApiClient


# This helper returns the tool schemas exposed to the language model.
def build_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "check_package",
                "description": "Check the current status and location of a package.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "packageid": {
                            "type": "string",
                            "description": "The package identifier provided by the operator.",
                        }
                    },
                    "required": ["packageid"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "redirect_package",
                "description": "Redirect a package to a destination using a security code.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "packageid": {
                            "type": "string",
                            "description": "The package identifier provided by the operator.",
                        },
                        "destination": {
                            "type": "string",
                            "description": "The destination code requested during the conversation.",
                        },
                        "code": {
                            "type": "string",
                            "description": "The security code provided by the operator.",
                        },
                    },
                    "required": ["packageid", "destination", "code"],
                    "additionalProperties": False,
                },
            },
        },
    ]


# This toolbox coordinates tool dispatch between the agent and the API client.
class ProxyToolbox:
    # This initializer wires configuration and the packages API client into the toolbox.
    def __init__(
        self,
        config: AppConfig,
        api_client: PackageApiClient | None = None,
    ) -> None:
        self.config = config
        self.api_client = api_client or PackageApiClient(config)

    # This method will validate and execute one tool call for the current session.
    def dispatch_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        session_state: SessionState,
    ) -> ToolExecutionResult:
        raise NotImplementedError(
            "Tool dispatch and hidden redirect enforcement will be implemented in a later step."
        )
