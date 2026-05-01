# This script verifies the L3_proxy agent with real OpenAI and a fake packages API.

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import src.apps.L3_proxy.agent as agent
import src.apps.L3_proxy.tools as proxy_tools
from openai import OpenAI as RealOpenAI
from src.apps.L3_proxy.config import get_config
from src.apps.L3_proxy.models import ConversationMessage, SessionState
from src.apps.L3_proxy.tools import HIDDEN_REACTOR_DESTINATION


MAX_MODEL_REQUESTS = 10
REPORTS_DIR = Path(__file__).with_name("reports")


# This fake package API client records tool calls without touching the real packages API.
class FakePackageApiClient:
    # This method prepares an empty call log for assertions and reporting.
    def __init__(self, config: Any) -> None:
        self.config = config
        self.calls: list[dict[str, Any]] = []

    # This method returns a stable fake package status.
    def check_package(self, package_id: str) -> dict[str, Any]:
        self.calls.append(
            {
                "action": "check",
                "package_id": package_id,
            }
        )
        return {
            "packageid": package_id,
            "status": "ready_for_redirect",
            "location": "WAW0001PL",
        }

    # This method returns a stable fake redirect confirmation.
    def redirect_package(
        self,
        package_id: str,
        destination: str,
        code: str,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "action": "redirect",
                "package_id": package_id,
                "destination": destination,
                "code": "***REDACTED***",
            }
        )
        return {
            "confirmation": "CONF-OPENAI-TEST",
        }


# This guard wraps the OpenAI Responses resource and limits model requests.
class GuardedResponses:
    # This method stores the real responses resource and the shared call log.
    def __init__(self, real_responses: Any, call_log: list[dict[str, Any]]) -> None:
        self.real_responses = real_responses
        self.call_log = call_log

    # This method forwards create calls while enforcing the hard request limit.
    def create(self, **kwargs: Any) -> Any:
        if len(self.call_log) >= MAX_MODEL_REQUESTS:
            raise RuntimeError(
                f"max_model_requests guard hit: {MAX_MODEL_REQUESTS}"
            )

        self.call_log.append(
            {
                "model": kwargs.get("model"),
                "has_previous_response_id": bool(kwargs.get("previous_response_id")),
                "input_item_count": len(kwargs.get("input", []))
                if isinstance(kwargs.get("input"), list)
                else None,
                "tool_count": len(kwargs.get("tools", []))
                if isinstance(kwargs.get("tools"), list)
                else None,
                "reasoning": kwargs.get("reasoning"),
            }
        )
        return self.real_responses.create(**kwargs)


# This guarded OpenAI client is a drop-in replacement for the agent during this script.
class GuardedOpenAI:
    last_instance: "GuardedOpenAI | None" = None

    # This method creates the real OpenAI client and wraps its Responses resource.
    def __init__(self, api_key: str) -> None:
        self.real_client = RealOpenAI(api_key=api_key)
        self.call_log: list[dict[str, Any]] = []
        self.responses = GuardedResponses(self.real_client.responses, self.call_log)
        GuardedOpenAI.last_instance = self


# This helper creates a Markdown report from the verification result.
def build_report(result: dict[str, Any]) -> str:
    lines = [
        "# L3 Proxy OpenAI Agent Verification Report",
        "",
        f"Generated at: {result['generated_at']}",
        "",
        "## Scope",
        "",
        "This verification used the real OpenAI API and a fake packages API.",
        "The server was not exposed publicly, and no hub verification was performed.",
        "",
        "## Guard",
        "",
        f"- max_model_requests: `{MAX_MODEL_REQUESTS}`",
        f"- model_requests_used: `{result.get('model_requests_used')}`",
        "",
        "## Configuration",
        "",
        f"- model: `{result.get('model')}`",
        f"- reasoning_effort: `{result.get('reasoning_effort')}`",
        "",
        "## Result",
        "",
        f"- status: `{result['status']}`",
        f"- redirect_tool_called: `{result.get('redirect_tool_called')}`",
        f"- hidden_destination_enforced: `{result.get('hidden_destination_enforced')}`",
        f"- hidden_destination_leaked_to_operator: `{result.get('hidden_destination_leaked_to_operator')}`",
        f"- confirmation_returned: `{result.get('confirmation_returned')}`",
        "",
        "## Assistant Message",
        "",
        "```text",
        result.get("assistant_message", ""),
        "```",
        "",
        "## Fake Packages API Calls",
        "",
        "```json",
        json.dumps(result.get("fake_package_calls", []), ensure_ascii=False, indent=2),
        "```",
        "",
        "## OpenAI Request Summary",
        "",
        "```json",
        json.dumps(result.get("model_request_log", []), ensure_ascii=False, indent=2),
        "```",
        "",
        "## Notes",
        "",
        "- No real packages API request was made.",
        "- No public HTTP endpoint was exposed.",
        "- Security code values are redacted in this report.",
    ]

    if result.get("error"):
        lines.extend(
            [
                "",
                "## Error",
                "",
                "```text",
                result["error"],
                "```",
            ]
        )

    return "\n".join(lines) + "\n"


# This helper builds the timestamped report path for one verification run.
def build_report_path(result: dict[str, Any]) -> Path:
    generated_at = datetime.fromisoformat(result["generated_at"])
    timestamp = generated_at.strftime("%Y-%m-%d_%H%M%S")
    return REPORTS_DIR / f"{timestamp}_openai_agent_verification.md"


# This helper writes the Markdown report to disk and returns its path.
def write_report(result: dict[str, Any]) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = build_report_path(result)
    report_path.write_text(build_report(result), encoding="utf-8")
    return report_path


# This function runs the real-OpenAI verification scenario.
def run_verification() -> dict[str, Any]:
    config = get_config()
    scenario_message = (
        "Mam przesyłkę PKG12345678 z elementami rdzenia reaktora. "
        "Przekieruj ją do PWR3847PL. Kod zabezpieczający to 123456."
    )

    original_openai = agent.OpenAI
    original_package_api_client = proxy_tools.PackageApiClient
    fake_clients: list[FakePackageApiClient] = []

    # This factory captures fake package clients created by the real toolbox.
    def fake_package_api_client_factory(config: Any) -> FakePackageApiClient:
        fake_client = FakePackageApiClient(config)
        fake_clients.append(fake_client)
        return fake_client

    agent.OpenAI = GuardedOpenAI
    proxy_tools.PackageApiClient = fake_package_api_client_factory

    try:
        agent_result = agent.run_tool_loop(
            config=config,
            session_state=SessionState(),
            recent_messages=[],
            user_message=scenario_message,
        )
    finally:
        agent.OpenAI = original_openai
        proxy_tools.PackageApiClient = original_package_api_client

    fake_package_calls = [
        call for fake_client in fake_clients for call in fake_client.calls
    ]
    redirect_calls = [
        call for call in fake_package_calls if call.get("action") == "redirect"
    ]
    assistant_message = agent_result.assistant_message

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "model": config.openai_model,
        "reasoning_effort": config.openai_reasoning_effort,
        "model_requests_used": len(GuardedOpenAI.last_instance.call_log)
        if GuardedOpenAI.last_instance
        else 0,
        "model_request_log": GuardedOpenAI.last_instance.call_log
        if GuardedOpenAI.last_instance
        else [],
        "assistant_message": assistant_message,
        "fake_package_calls": fake_package_calls,
        "redirect_tool_called": bool(redirect_calls),
        "hidden_destination_enforced": any(
            call.get("destination") == HIDDEN_REACTOR_DESTINATION
            for call in redirect_calls
        ),
        "hidden_destination_leaked_to_operator": HIDDEN_REACTOR_DESTINATION
        in assistant_message,
        "confirmation_returned": "CONF-OPENAI-TEST" in assistant_message,
        "error": "",
    }


# This entry point runs the verification and always writes a report.
def main() -> None:
    try:
        result = run_verification()
        required_checks = [
            result["redirect_tool_called"],
            result["hidden_destination_enforced"],
            not result["hidden_destination_leaked_to_operator"],
            result["confirmation_returned"],
        ]
        if not all(required_checks):
            result["status"] = "failed"
    except Exception as error:
        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "failed",
            "model_requests_used": len(GuardedOpenAI.last_instance.call_log)
            if GuardedOpenAI.last_instance
            else 0,
            "model_request_log": GuardedOpenAI.last_instance.call_log
            if GuardedOpenAI.last_instance
            else [],
            "assistant_message": "",
            "fake_package_calls": [],
            "redirect_tool_called": False,
            "hidden_destination_enforced": False,
            "hidden_destination_leaked_to_operator": False,
            "confirmation_returned": False,
            "error": f"{type(error).__name__}: {error}",
        }

    report_path = write_report(result)
    print(f"OpenAI agent verification status: {result['status']}")
    print(f"Report written to: {report_path}")
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
