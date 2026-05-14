# Fetch the railway API help response once and save it for reading.

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()

TASK_NAME = "railway"
OUTPUT_FILE = Path("data/L5_railway/output/help_response.json")
REQUEST_TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 5
INITIAL_BACKOFF_SECONDS = 2


# Read a required environment variable with a clear setup error.
def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing. Add it to .env.")

    return value


# Decode a response as JSON when possible, otherwise preserve raw text.
def decode_response(response: requests.Response) -> Any:
    try:
        return response.json()
    except requests.JSONDecodeError:
        return response.text


# Fetch the help response and retry when the API simulates overload with HTTP 503.
def fetch_help_response(verify_url: str, payload: dict[str, Any]) -> tuple[requests.Response, int]:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = requests.post(verify_url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code != 503 or attempt == MAX_ATTEMPTS:
            return response, attempt

        wait_seconds = INITIAL_BACKOFF_SECONDS * attempt
        print(f"HTTP 503 on attempt {attempt}/{MAX_ATTEMPTS}. Waiting {wait_seconds}s before retry.")
        time.sleep(wait_seconds)

    raise RuntimeError("The help request did not run.")


api_key = get_required_env("AI_DEVS_API_KEY")
verify_url = get_required_env("HUB_VERIFY_URL")

payload = {
    "apikey": api_key,
    "task": TASK_NAME,
    "answer": {
        "action": "help",
    },
}

response, attempts_used = fetch_help_response(verify_url, payload)
result = {
    "attempts": attempts_used,
    "http_status": response.status_code,
    "body": decode_response(response),
}

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE.write_text(
    json.dumps(result, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(f"Saved help response to {OUTPUT_FILE}")
print(f"HTTP status: {response.status_code}")
print(f"Attempts used: {attempts_used}")
