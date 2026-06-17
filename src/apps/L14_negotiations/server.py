# This module exposes the local HTTP tool endpoint for L14_negotiations.

from __future__ import annotations

from datetime import datetime
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import traceback
from typing import Any

from .availability import build_tool_output
from .catalog_loader import Catalog, load_catalog
from .config import (
    DEFAULT_MAX_REQUEST_BYTES,
    AppConfig,
    apply_repository_tls_ca_setup,
    ensure_runtime_directories,
    get_llm_config,
)
from .matcher import match_needs
from .query_interpreter import QueryInterpreter
from .schemas import build_tool_response, parse_tool_request


FALLBACK_INTERPRETATION_ERROR = (
    "Nie mog\u0119 teraz zinterpretowa\u0107 zapytania. "
    "Spr\u00f3buj pro\u015bciej."
)


# This error represents an HTTP request body that exceeds the configured limit.
class RequestBodyTooLargeError(ValueError):
    pass


# Append one unexpected runtime failure to the app log file for later debugging.
def append_runtime_error_log(log_path: Path | None, error: Exception) -> None:
    if log_path is None:
        return

    timestamp = datetime.now().isoformat(timespec="seconds")
    traceback_text = traceback.format_exc()
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(
            f"[{timestamp}] Unexpected L14_negotiations POST failure: "
            f"{error.__class__.__name__}: {error}\n"
        )
        log_file.write(traceback_text)
        log_file.write("\n")


# This handler validates tool requests and returns compact Polish answers.
class NegotiationsRequestHandler(BaseHTTPRequestHandler):
    catalog: Catalog | None = None
    interpreter: QueryInterpreter | None = None
    error_log_path: Path | None = None
    max_request_bytes = DEFAULT_MAX_REQUEST_BYTES

    # Handle one tool request from the external course agent.
    def do_POST(self) -> None:
        if self.path != "/":
            self.send_json(404, {"error": "Endpoint not found."})
            return

        try:
            payload = self.read_json_body()
        except RequestBodyTooLargeError as error:
            self.send_json(413, {"error": str(error)})
            return
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
            return

        if self.catalog is None or self.interpreter is None:
            self.send_json(503, {"error": "Tool service is not initialized."})
            return

        try:
            response = process_tool_request(payload, self.catalog, self.interpreter)
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
            return
        except Exception as error:
            append_runtime_error_log(self.error_log_path, error)
            # Keep model or runtime details out of the public tool contract.
            self.send_json(
                200,
                build_tool_response(FALLBACK_INTERPRETATION_ERROR),
            )
            return

        self.send_json(200, response)

    # Return a small JSON health response for local startup checks.
    def do_GET(self) -> None:
        if self.path != "/":
            self.send_json(404, {"error": "Endpoint not found."})
            return

        summary = self.catalog.summary() if self.catalog else {}
        self.send_json(
            200,
            {
                "status": "ok",
                "task": "negotiations",
                "catalog": summary,
            },
        )

    # Read and validate the incoming JSON request body.
    def read_json_body(self) -> dict[str, Any]:
        content_length_header = self.headers.get("Content-Length", "")
        try:
            content_length = int(content_length_header)
        except ValueError as error:
            raise ValueError("Content-Length must be an integer.") from error

        if content_length <= 0:
            raise ValueError("Request body cannot be empty.")
        if content_length > self.max_request_bytes:
            raise RequestBodyTooLargeError(
                f"Request body cannot be larger than {self.max_request_bytes} bytes."
            )

        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("Request body must be valid JSON.") from error

        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")

        return payload

    # Write one JSON response with consistent headers.
    def send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        response_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    # Suppress default HTTP logging so app logs can stay deliberate later.
    def log_message(self, format: str, *args: Any) -> None:
        return


# Start the local HTTP server after validating catalog data.
def run_server(config: AppConfig) -> None:
    ensure_runtime_directories(config)
    apply_repository_tls_ca_setup(config.paths)
    NegotiationsRequestHandler.catalog = load_catalog(config)
    NegotiationsRequestHandler.interpreter = QueryInterpreter(get_llm_config())
    NegotiationsRequestHandler.error_log_path = (
        config.paths.logs_dir / "server_runtime_errors.log"
    )
    NegotiationsRequestHandler.max_request_bytes = config.server.max_request_bytes

    server = ThreadingHTTPServer(
        (config.server.host, config.server.port),
        NegotiationsRequestHandler,
    )
    print(
        "L14_negotiations server listening on "
        f"http://{config.server.host}:{config.server.port}/"
    )
    server.serve_forever()


# Execute the full request pipeline with injectable dependencies for local tests.
def process_tool_request(
    payload: dict[str, object],
    catalog: Catalog,
    interpreter: QueryInterpreter,
) -> dict[str, str]:
    request = parse_tool_request(payload)
    interpretation = interpreter.interpret(request.params)
    match_results = match_needs(interpretation.items, catalog)
    output = build_tool_output(interpretation, match_results, catalog)
    return build_tool_response(output)
