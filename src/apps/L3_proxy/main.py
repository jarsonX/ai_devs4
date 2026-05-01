# This module is the local application entry point for the L3_proxy app.

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .config import DEFAULT_MAX_REQUEST_BYTES, ensure_runtime_directories, get_config
from .pipeline import handle_request


# This error represents an HTTP request body that exceeds the configured limit.
class RequestBodyTooLargeError(ValueError):
    pass


# This HTTP handler exposes the proxy pipeline as a JSON POST endpoint.
class ProxyRequestHandler(BaseHTTPRequestHandler):
    max_request_bytes = DEFAULT_MAX_REQUEST_BYTES

    # This method handles the operator-facing proxy request.
    def do_POST(self) -> None:
        if self.path != "/":
            self.send_json(404, {"error": "Endpoint not found."})
            return

        try:
            payload = self.read_json_body()
            response_payload = handle_request(payload)
        except RequestBodyTooLargeError as error:
            self.send_json(413, {"error": str(error)})
            return
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
            return
        except Exception:
            self.send_json(500, {"error": "Internal server error."})
            return

        self.send_json(200, response_payload)

    # This method keeps unsupported GET requests explicit and JSON-shaped.
    def do_GET(self) -> None:
        self.send_json(405, {"error": "Use POST with a JSON body."})

    # This helper reads and validates the incoming JSON request body.
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

    # This helper writes one JSON response with consistent headers.
    def send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        response_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    # This method routes default HTTP server logs through the console.
    def log_message(self, format: str, *args: Any) -> None:
        return


# This function starts the local HTTP server for the proxy app.
def run_app() -> None:
    config = get_config()
    ensure_runtime_directories(config)
    ProxyRequestHandler.max_request_bytes = config.max_request_bytes

    server = ThreadingHTTPServer(
        (config.app_host, config.app_port),
        ProxyRequestHandler,
    )
    print(f"L3_proxy server listening on http://{config.app_host}:{config.app_port}/")
    server.serve_forever()


if __name__ == "__main__":
    run_app()
