# This module registers the public negotiations tool URL with the course Hub.

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from typing import Any

import requests

from .config import HubConfig, apply_repository_tls_ca_setup, get_hub_config


REDACTED = "***REDACTED***"
MAX_VERIFY_REQUESTS = 2
FLAG_PATTERN = re.compile(r"\{FLG:[^}]+}")

TOOL_DESCRIPTION = (
    "Polskie narzedzie: przekaz w params opis 1-3 produktow. "
    "Zwraca po polsku miasta, ktore maja wszystkie dopasowane produkty."
)


# Preserve one Hub response in a stable shape for CLI output and tests.
@dataclass(frozen=True)
class HubResponse:
    status_code: int
    payload: Any
    text: str


# Validate the public tool URL before it reaches the Hub payload.
def validate_public_url(public_url: str) -> str:
    normalized_url = public_url.strip()
    if not normalized_url:
        raise ValueError("Public tool URL cannot be empty.")
    if not normalized_url.startswith(("http://", "https://")):
        raise ValueError("Public tool URL must start with http:// or https://.")
    return normalized_url


# Build the exact tools registration payload expected by the negotiations task.
def build_register_payload(config: HubConfig, public_tool_url: str) -> dict[str, Any]:
    return {
        "apikey": config.api_key,
        "task": config.task_name,
        "answer": {
            "tools": [
                {
                    "URL": validate_public_url(public_tool_url),
                    "description": TOOL_DESCRIPTION,
                }
            ]
        },
    }


# Build the async status-check payload expected after tool registration.
def build_check_payload(config: HubConfig) -> dict[str, Any]:
    return {
        "apikey": config.api_key,
        "task": config.task_name,
        "answer": {
            "action": "check",
        },
    }


# Mask the API key before a payload is printed or written anywhere.
def mask_payload_for_display(payload: dict[str, Any]) -> dict[str, Any]:
    masked_payload = dict(payload)
    if "apikey" in masked_payload:
        masked_payload["apikey"] = REDACTED
    return masked_payload


# Detect whether a Hub response contains a course flag.
def extract_flag(value: Any) -> str | None:
    if isinstance(value, str):
        match = FLAG_PATTERN.search(value)
        return match.group(0) if match else None
    if isinstance(value, dict):
        for nested_value in value.values():
            flag = extract_flag(nested_value)
            if flag:
                return flag
    if isinstance(value, list):
        for nested_value in value:
            flag = extract_flag(nested_value)
            if flag:
                return flag
    return None


# Convert one HTTP response into a stable object.
def build_hub_response(response: requests.Response) -> HubResponse:
    try:
        payload = response.json()
    except ValueError:
        payload = None
    return HubResponse(
        status_code=response.status_code,
        payload=payload,
        text=response.text,
    )


# Keep Hub requests bounded before any external request is sent.
class VerifyRequestGuard:
    # Store the request cap for one helper process.
    def __init__(self, max_requests: int = MAX_VERIFY_REQUESTS) -> None:
        self.max_requests = max_requests
        self.used_requests = 0

    # Count one planned request and stop before the Hub call when capped.
    def consume(self) -> None:
        if self.used_requests >= self.max_requests:
            raise RuntimeError(f"Hub request guard reached {self.max_requests} calls.")
        self.used_requests += 1


# Submit guarded negotiations registration and status-check requests.
class HubClient:
    # Store Hub config plus an injectable HTTP session for local tests.
    def __init__(
        self,
        config: HubConfig,
        *,
        session: requests.Session | Any | None = None,
        guard: VerifyRequestGuard | None = None,
    ) -> None:
        self.config = config
        self.session = session or requests.Session()
        self.guard = guard or VerifyRequestGuard()

    # Register the public tool URL and return masked request data plus Hub feedback.
    def register_tools(self, public_tool_url: str) -> tuple[dict[str, Any], HubResponse]:
        self.guard.consume()
        payload = build_register_payload(self.config, public_tool_url)
        response = self.session.post(
            self.config.verify_url,
            json=payload,
            timeout=self.config.request_timeout_seconds,
        )
        return mask_payload_for_display(payload), build_hub_response(response)

    # Ask the Hub for the async negotiations verification status.
    def check_status(self) -> tuple[dict[str, Any], HubResponse]:
        self.guard.consume()
        payload = build_check_payload(self.config)
        response = self.session.post(
            self.config.verify_url,
            json=payload,
            timeout=self.config.request_timeout_seconds,
        )
        return mask_payload_for_display(payload), build_hub_response(response)


# Parse the explicit registration or async-check command.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Register or check the L14_negotiations public tool URL.",
    )
    parser.add_argument(
        "public_url",
        nargs="?",
        help="Public URL pointing to the L14_negotiations POST endpoint.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check asynchronous negotiations verification status instead of registering tools.",
    )
    return parser.parse_args()


# Print one masked request and the matching Hub response.
def print_result(masked_payload: dict[str, Any], response: HubResponse) -> None:
    print("Payload sent to hub:")
    print(json.dumps(masked_payload, ensure_ascii=False, indent=2))
    print("\nHub response:")
    print(f"HTTP status: {response.status_code}")
    if response.payload is None:
        print(response.text)
    else:
        print(json.dumps(response.payload, ensure_ascii=False, indent=2))
    if extract_flag(response.payload) or extract_flag(response.text):
        print("\nFlag detected in Hub response. Keep raw value only in ignored runtime data.")


# Run one explicit Hub helper command.
def main() -> None:
    args = parse_args()
    if not args.check and not args.public_url:
        raise SystemExit("public_url is required unless --check is used.")

    apply_repository_tls_ca_setup()
    client = HubClient(get_hub_config())

    if args.check:
        masked_payload, response = client.check_status()
    else:
        masked_payload, response = client.register_tools(args.public_url)

    print_result(masked_payload, response)


if __name__ == "__main__":
    main()
