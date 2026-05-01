# This module submits the public L3_proxy endpoint URL to the course verification hub.

from __future__ import annotations

import argparse
import json
from typing import Any
from uuid import uuid4

import requests

from .config import AppConfig, get_config


REQUEST_TIMEOUT_SECONDS = 30
REDACTED = "***REDACTED***"


# This helper validates the public endpoint URL before submitting it to the hub.
def validate_public_url(public_url: str) -> str:
    normalized_url = public_url.strip()
    if not normalized_url:
        raise ValueError("Public endpoint URL cannot be empty.")
    if not normalized_url.startswith(("http://", "https://")):
        raise ValueError("Public endpoint URL must start with http:// or https://.")

    return normalized_url


# This helper builds a stable verification payload for the course hub.
def build_verification_payload(
    config: AppConfig,
    public_url: str,
    session_id: str,
) -> dict[str, Any]:
    return {
        "apikey": config.ai_devs_api_key,
        "task": config.task_name,
        "answer": {
            "url": validate_public_url(public_url),
            "sessionID": session_id,
        },
    }


# This helper masks only the API key while leaving the public endpoint visible for review.
def mask_payload_for_display(payload: dict[str, Any]) -> dict[str, Any]:
    masked_payload = dict(payload)
    masked_payload["apikey"] = REDACTED
    return masked_payload


# This helper posts the verification payload and returns response details for display.
def submit_verification(config: AppConfig, payload: dict[str, Any]) -> tuple[int, Any]:
    response = requests.post(
        config.verify_api_url,
        json=payload,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    try:
        response_body: Any = response.json()
    except requests.JSONDecodeError:
        response_body = response.text

    return response.status_code, response_body


# This helper parses command-line arguments for one verification submission.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Submit the public L3_proxy endpoint URL to the course hub.",
    )
    parser.add_argument(
        "public_url",
        help="Public pinggy URL pointing to the L3_proxy POST endpoint.",
    )
    parser.add_argument(
        "--session-id",
        default=f"proxy-{uuid4().hex[:12]}",
        help="Session ID that the hub should use during verification.",
    )
    return parser.parse_args()


# This function runs one verification submission and prints the hub response.
def main() -> None:
    args = parse_args()
    config = get_config()
    payload = build_verification_payload(
        config=config,
        public_url=args.public_url,
        session_id=args.session_id,
    )

    print("Payload sent to hub:")
    print(json.dumps(mask_payload_for_display(payload), ensure_ascii=False, indent=2))

    status_code, response_body = submit_verification(config, payload)

    print("\nHub response:")
    print(f"HTTP status: {status_code}")
    if isinstance(response_body, str):
        print(response_body)
    else:
        print(json.dumps(response_body, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
