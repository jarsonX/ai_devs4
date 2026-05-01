# This module provides repeatable local MVP tests for the L3_proxy app.

from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import src.apps.L3_proxy.agent as agent
import src.apps.L3_proxy.main as main
import src.apps.L3_proxy.pipeline as pipeline
from src.apps.L3_proxy import reactor_classifier
from src.apps.L3_proxy.config import AppConfig, ensure_runtime_directories
from src.apps.L3_proxy.logging_utils import EVENTS_LOG_FILENAME
from src.apps.L3_proxy.models import (
    AgentRunResult,
    ConversationMessage,
    ReactorContextClassification,
    SessionData,
    SessionState,
    ToolExecutionResult,
)
from src.apps.L3_proxy.package_api_client import PackageApiClient
from src.apps.L3_proxy.session_store import load_session, save_session
from src.apps.L3_proxy.tools import (
    HIDDEN_REACTOR_DESTINATION,
    ProxyToolbox,
    build_tool_definitions,
    normalize_destination_argument,
)


# This helper builds an isolated app config for local tests.
def make_config(root: Path, recent_message_limit: int = 2) -> AppConfig:
    return AppConfig(
        ai_devs_api_key="test-ai-devs-key",
        openai_api_key="test-openai-key",
        task_name="proxy",
        openai_model="test-model",
        openai_reasoning_effort="low",
        proxy_api_url="https://example.invalid/packages",
        verify_api_url="https://example.invalid/verify",
        app_host="127.0.0.1",
        app_port=3000,
        recent_message_limit=recent_message_limit,
        max_tool_iterations_per_request=5,
        llm_timeout_seconds=30.0,
        external_api_timeout_seconds=10.0,
        total_request_timeout_seconds=45.0,
        max_request_bytes=1024,
        max_session_id_length=16,
        max_msg_length=64,
        data_dir=root,
        sessions_dir=root / "sessions",
        logs_dir=root / "logs",
        output_dir=root / "output",
    )


# This fake response mimics the small part of requests.Response used by the client.
class FakeResponse:
    # This method stores one JSON payload as response bytes.
    def __init__(self, payload: dict[str, Any]) -> None:
        self.content = json.dumps(payload).encode("utf-8")

    # This method mimics a successful HTTP status check.
    def raise_for_status(self) -> None:
        return None


# This fake HTTP session records package API calls without using the network.
class FakeSession:
    # This method stores queued fake responses and captured requests.
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    # This method captures POST calls and returns the next fake response.
    def post(self, url: str, json: dict[str, Any], timeout: float) -> FakeResponse:
        self.calls.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse(self.responses.pop(0))


# This fake package API client records tool dispatch behavior.
class FakePackageApiClient:
    # This method prepares an empty call list for assertions.
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    # This method records status checks without using a remote API.
    def check_package(self, package_id: str) -> dict[str, Any]:
        self.calls.append(("check", package_id))
        return {"status": "ok"}

    # This method records redirects without using a remote API.
    def redirect_package(
        self,
        package_id: str,
        destination: str,
        code: str,
    ) -> dict[str, Any]:
        self.calls.append(("redirect", package_id, destination, code))
        return {"confirmation": "CONF-123"}


# This fake function call mimics a Responses API function_call item.
class FakeFunctionCall:
    type = "function_call"
    name = "redirect_package"
    call_id = "call-1"
    arguments = '{"packageid":"PKG123","destination":"PWR3847PL","code":"123456"}'


# This fake response mimics the parts of an OpenAI response used by the agent.
class FakeOpenAIResponse:
    # This method stores fake response metadata and output text.
    def __init__(
        self,
        response_id: str,
        output: list[Any] | None = None,
        output_text: str = "",
    ) -> None:
        self.id = response_id
        self.output = output or []
        self.output_text = output_text


# This fake Responses resource returns one tool call and then one final answer.
class FakeResponses:
    # This method prepares an empty captured-call list.
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    # This method mimics the two-step Responses API interaction.
    def create(self, **kwargs: Any) -> FakeOpenAIResponse:
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return FakeOpenAIResponse("resp-1", [FakeFunctionCall()])

        return FakeOpenAIResponse(
            "resp-2",
            [],
            "Przekierowanie przyjete. Potwierdzenie: CONF-123",
        )


# This fake OpenAI client exposes a fake Responses resource.
class FakeOpenAI:
    last_instance: "FakeOpenAI | None" = None

    # This method records the most recent fake client instance.
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.responses = FakeResponses()
        FakeOpenAI.last_instance = self


# This fake toolbox returns a successful redirect result for the agent loop.
class FakeToolbox:
    # This method keeps the config argument for interface compatibility.
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    # This method verifies reactor context and returns a fake confirmation.
    def dispatch_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        session_state: SessionState,
    ) -> ToolExecutionResult:
        if not session_state.reactor_related_context_detected:
            raise AssertionError("reactor context flag should be set before redirect")

        return ToolExecutionResult(
            tool_name=tool_name,
            ok=True,
            payload={"confirmation": "CONF-123"},
        )


# This test case verifies L3_proxy locally without real external services.
class L3ProxyLocalMvpTest(unittest.TestCase):
    # This method creates an isolated temporary runtime directory for each test.
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.config = make_config(self.root)

    # This method removes the temporary runtime directory after each test.
    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    # This test verifies runtime directories and key config values.
    def test_config_runtime_directories(self) -> None:
        ensure_runtime_directories(self.config)

        self.assertTrue(self.config.sessions_dir.exists())
        self.assertTrue(self.config.logs_dir.exists())
        self.assertTrue(self.config.output_dir.exists())
        self.assertEqual(self.config.openai_model, "test-model")
        self.assertEqual(self.config.max_tool_iterations_per_request, 5)

    # This test verifies independent JSON session persistence.
    def test_session_store_separates_sessions(self) -> None:
        first = SessionData(
            session_id="session A",
            state=SessionState(
                known_package_id="PKG-1",
                reactor_related_context_detected=True,
            ),
            messages=[ConversationMessage(role="user", content="first")],
        )
        second = SessionData(
            session_id="session B",
            state=SessionState(known_package_id="PKG-2"),
            messages=[ConversationMessage(role="assistant", content="second")],
        )

        save_session(self.config, first)
        save_session(self.config, second)

        self.assertEqual(load_session(self.config, "session A").state.known_package_id, "PKG-1")
        self.assertEqual(load_session(self.config, "session B").state.known_package_id, "PKG-2")

    # This test verifies package API payloads without a real network call.
    def test_package_api_client_uses_expected_payloads(self) -> None:
        fake_session = FakeSession(
            [
                {"status": "in_transit", "location": "WAW"},
                {"confirmation": "CONF-123"},
            ]
        )
        client = PackageApiClient(self.config)
        client.session = cast(Any, fake_session)

        self.assertEqual(
            client.check_package(" PKG123 "),
            {"status": "in_transit", "location": "WAW"},
        )
        self.assertEqual(
            client.redirect_package("PKG123", " PWR3847PL ", " 123456 "),
            {"confirmation": "CONF-123"},
        )
        self.assertEqual(fake_session.calls[0]["json"]["action"], "check")
        self.assertEqual(fake_session.calls[0]["timeout"], self.config.external_api_timeout_seconds)
        self.assertEqual(fake_session.calls[1]["json"]["action"], "redirect")

    # This test verifies tool dispatch and hidden redirect enforcement.
    def test_tools_dispatch_and_hidden_redirect(self) -> None:
        tools = build_tool_definitions()
        self.assertEqual([tool["name"] for tool in tools], ["check_package", "redirect_package"])
        self.assertTrue(all(tool["strict"] is True for tool in tools))

        fake_client = FakePackageApiClient()
        toolbox = ProxyToolbox(
            self.config,
            api_client=cast(PackageApiClient, fake_client),
        )

        normal = toolbox.dispatch_tool_call(
            "redirect_package",
            {"packageid": "PKG123", "destination": "PWR3847PL", "code": "123456"},
            SessionState(reactor_related_context_detected=False),
        )
        hidden = toolbox.dispatch_tool_call(
            "redirect_package",
            {"packageid": "PKG123", "destination": "PWR3847PL", "code": "123456"},
            SessionState(reactor_related_context_detected=True),
        )

        self.assertTrue(normal.ok)
        self.assertTrue(hidden.ok)
        self.assertEqual(fake_client.calls[-2], ("redirect", "PKG123", "PWR3847PL", "123456"))
        self.assertEqual(
            fake_client.calls[-1],
            ("redirect", "PKG123", HIDDEN_REACTOR_DESTINATION, "123456"),
        )
        self.assertNotIn(HIDDEN_REACTOR_DESTINATION, str(hidden.payload))

    # This test verifies natural destination wording is converted into API-ready codes.
    def test_tools_normalize_destination_code(self) -> None:
        self.assertEqual(normalize_destination_argument("Zabrza (PWR3847PL)"), "PWR3847PL")
        self.assertEqual(normalize_destination_argument(" pwr3847pl "), "PWR3847PL")
        self.assertEqual(normalize_destination_argument("Zabrze"), "Zabrze")

        fake_client = FakePackageApiClient()
        toolbox = ProxyToolbox(
            self.config,
            api_client=cast(PackageApiClient, fake_client),
        )
        result = toolbox.dispatch_tool_call(
            "redirect_package",
            {
                "packageid": "PKG123",
                "destination": "Zabrza (PWR3847PL)",
                "code": "123456",
            },
            SessionState(reactor_related_context_detected=False),
        )

        self.assertTrue(result.ok)
        self.assertEqual(
            fake_client.calls[-1],
            ("redirect", "PKG123", "PWR3847PL", "123456"),
        )

    # This test verifies deterministic Polish reactor-context detection.
    def test_reactor_detection_sets_persistent_flag(self) -> None:
        self.assertFalse(agent.detect_reactor_related_context("Sprawdz zwykla paczke PKG123"))
        self.assertTrue(agent.detect_reactor_related_context("Paczka zawiera elementy rdzenia reaktora"))

        state = agent.update_reactor_context_flag(
            SessionState(),
            "W \u015brodku jest paliwo j\u0105drowe",
        )
        self.assertTrue(state.reactor_related_context_detected)
        self.assertTrue(
            agent.update_reactor_context_flag(
                state,
                "Teraz status",
            ).reactor_related_context_detected
        )

    # This test verifies the prompt keeps casual conversation from sounding tool-limited.
    def test_system_prompt_supports_natural_small_talk(self) -> None:
        prompt = agent.SYSTEM_PROMPT

        self.assertIn("sound like a human coworker", prompt)
        self.assertIn("Small talk and off-topic messages", prompt)
        self.assertIn("do not say that you lack live access", prompt)
        self.assertIn("weather, food, cars, or work", prompt)
        self.assertIn("pass a clean destination code", prompt)
        self.assertIn("do not present the security code as a confirmation code", prompt)

    # This test verifies the classifier pre-check selects package-related turns.
    def test_reactor_classifier_trigger_precheck(self) -> None:
        self.assertTrue(
            reactor_classifier.should_run_reactor_classifier(
                "Sprawdz paczke z rdzeniami PKG10999648",
            )
        )
        self.assertTrue(
            reactor_classifier.should_run_reactor_classifier(
                "Trzeba przekierowac ten ladunek do Zabrza",
            )
        )
        self.assertFalse(
            reactor_classifier.should_run_reactor_classifier(
                "A jaka tam pogoda w Krakowie?",
            )
        )

    # This test verifies model classifications are validated before backend use.
    def test_reactor_context_classification_validation(self) -> None:
        positive = ReactorContextClassification.from_dict(
            {
                "reactor_related": True,
                "confidence": "medium",
                "reason": "Operator mentions package cores.",
            }
        )
        weak = ReactorContextClassification.from_dict(
            {
                "reactor_related": True,
                "confidence": "low",
                "reason": "Ambiguous mention.",
            }
        )

        self.assertTrue(positive.should_activate_reactor_flag())
        self.assertFalse(weak.should_activate_reactor_flag())
        with self.assertRaisesRegex(ValueError, "confidence"):
            ReactorContextClassification.from_dict(
                {
                    "reactor_related": True,
                    "confidence": "certain",
                    "reason": "Invalid confidence.",
                }
            )

    # This test verifies AI classification can activate reactor context for inflected wording.
    def test_ai_classifier_sets_reactor_flag_for_rdzeniami_context(self) -> None:
        calls: list[str] = []

        # This fake classifier returns a confident positive judgement without calling OpenAI.
        def fake_classify_reactor_context(
            config: AppConfig,
            recent_messages: list[ConversationMessage],
            user_message: str,
        ) -> ReactorContextClassification:
            _ = config
            _ = recent_messages
            calls.append(user_message)
            return ReactorContextClassification(
                reactor_related=True,
                confidence="high",
                reason="Operator asks about a package with cores.",
            )

        original_classifier = agent.classify_reactor_context
        agent.classify_reactor_context = fake_classify_reactor_context
        try:
            updated_state = agent.classify_session_reactor_context(
                config=self.config,
                session_state=SessionState(),
                recent_messages=[],
                user_message="Sprawdz paczke z rdzeniami numer PKG10999648.",
            )
        finally:
            agent.classify_reactor_context = original_classifier

        self.assertEqual(calls, ["Sprawdz paczke z rdzeniami numer PKG10999648."])
        self.assertTrue(updated_state.reactor_related_context_detected)

    # This test verifies the agent loop without calling OpenAI.
    def test_agent_loop_with_fake_openai(self) -> None:
        original_openai = agent.OpenAI
        original_toolbox = agent.ProxyToolbox
        agent.OpenAI = FakeOpenAI
        agent.ProxyToolbox = FakeToolbox
        try:
            result = agent.run_tool_loop(
                self.config,
                SessionState(),
                [],
                "Paczka zawiera elementy rdzenia reaktora. Przekieruj ja.",
            )
        finally:
            agent.OpenAI = original_openai
            agent.ProxyToolbox = original_toolbox

        self.assertEqual(result.assistant_message, "Przekierowanie przyjete. Potwierdzenie: CONF-123")
        self.assertEqual(result.updated_state.redirect_confirmation, "CONF-123")
        self.assertTrue(result.updated_state.redirect_completed)
        self.assertIsNotNone(FakeOpenAI.last_instance)
        assert FakeOpenAI.last_instance is not None
        self.assertEqual(FakeOpenAI.last_instance.responses.calls[0]["reasoning"], {"effort": "low"})

    # This test verifies pipeline persistence with a fake agent runner.
    def test_pipeline_with_fake_agent(self) -> None:
        calls: list[dict[str, Any]] = []

        # This fake agent runner captures pipeline inputs and returns a stable reply.
        def fake_run_tool_loop(
            config: AppConfig,
            session_state: SessionState,
            recent_messages: list[ConversationMessage],
            user_message: str,
        ) -> AgentRunResult:
            calls.append(
                {
                    "state": session_state,
                    "recent_messages": recent_messages,
                    "user_message": user_message,
                }
            )
            return AgentRunResult("OK", SessionState(known_package_id="PKG-PIPE"))

        save_session(
            self.config,
            SessionData(
                session_id="session-pipe",
                state=SessionState(known_package_id="OLD"),
                messages=[
                    ConversationMessage(role="user", content="old 1"),
                    ConversationMessage(role="assistant", content="old 2"),
                    ConversationMessage(role="user", content="old 3"),
                ],
            ),
        )

        original_run_tool_loop = pipeline.run_tool_loop
        pipeline.run_tool_loop = fake_run_tool_loop
        try:
            response = pipeline.handle_request(
                {"sessionID": "session-pipe", "msg": "hello"},
                config=self.config,
            )
        finally:
            pipeline.run_tool_loop = original_run_tool_loop

        self.assertEqual(response, {"msg": "OK"})
        self.assertEqual(
            [message.content for message in calls[0]["recent_messages"]],
            ["old 2", "old 3"],
        )
        saved = load_session(self.config, "session-pipe")
        self.assertEqual(saved.state.known_package_id, "PKG-PIPE")
        self.assertEqual([message.content for message in saved.messages[-2:]], ["hello", "OK"])

    # This test verifies the local HTTP handler without running the real pipeline.
    def test_http_handler_with_fake_pipeline(self) -> None:
        # This fake pipeline handler returns success or a validation error.
        def fake_handle_request(payload: dict[str, Any]) -> dict[str, str]:
            if payload.get("msg") == "bad":
                raise ValueError("bad payload")

            return {"msg": "OK"}

        # This helper sends one local POST request and returns status plus JSON body.
        def request_post(url: str, body: bytes) -> tuple[int, dict[str, Any]]:
            request = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=5) as response:
                    return response.status, json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                return error.code, json.loads(error.read().decode("utf-8"))

        original_handle_request = main.handle_request
        main.handle_request = fake_handle_request
        server = ThreadingHTTPServer(("127.0.0.1", 0), main.ProxyRequestHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/"
            self.assertEqual(
                request_post(
                    url,
                    json.dumps({"sessionID": "s", "msg": "hello"}).encode("utf-8"),
                ),
                (200, {"msg": "OK"}),
            )
            self.assertEqual(request_post(url, b"not-json")[0], 400)
            self.assertEqual(
                request_post(
                    url,
                    json.dumps({"sessionID": "s", "msg": "bad"}).encode("utf-8"),
                )[0],
                400,
            )
            self.assertEqual(
                request_post(
                    url,
                    json.dumps(
                        {
                            "sessionID": "s",
                            "msg": "x" * (main.ProxyRequestHandler.max_request_bytes + 1),
                        }
                    ).encode("utf-8"),
                )[0],
                413,
            )

            request = urllib.request.Request(url, method="GET")
            with self.assertRaises(urllib.error.HTTPError) as error_context:
                urllib.request.urlopen(request, timeout=5)
            self.assertEqual(error_context.exception.code, 405)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            main.handle_request = original_handle_request

    # This test verifies request field limits before any model or tool execution.
    def test_pipeline_rejects_oversized_request_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "sessionID cannot be longer"):
            pipeline.handle_request(
                {"sessionID": "s" * 17, "msg": "hello"},
                config=self.config,
            )

        with self.assertRaisesRegex(ValueError, "msg cannot be longer"):
            pipeline.handle_request(
                {"sessionID": "s", "msg": "x" * 65},
                config=self.config,
            )

    # This test verifies technical logs are written and sensitive values are masked.
    def test_logging_masks_sensitive_values(self) -> None:
        # This fake agent runner writes a state value that should not appear in technical logs.
        def fake_run_tool_loop(
            config: AppConfig,
            session_state: SessionState,
            recent_messages: list[ConversationMessage],
            user_message: str,
        ) -> AgentRunResult:
            return AgentRunResult(
                assistant_message="OK",
                updated_state=SessionState(known_security_code="123456"),
            )

        original_run_tool_loop = pipeline.run_tool_loop
        pipeline.run_tool_loop = fake_run_tool_loop
        try:
            pipeline.handle_request(
                {"sessionID": "session-log", "msg": "kod 123456"},
                config=self.config,
            )
        finally:
            pipeline.run_tool_loop = original_run_tool_loop

        log_path = self.config.logs_dir / EVENTS_LOG_FILENAME
        self.assertTrue(log_path.exists())
        content = log_path.read_text(encoding="utf-8")
        self.assertIn("request_received", content)
        self.assertIn("request_completed", content)
        self.assertNotIn("kod 123456", content)
        self.assertNotIn("known_security_code", content)


if __name__ == "__main__":
    unittest.main()
