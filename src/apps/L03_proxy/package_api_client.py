# This module defines the external packages API client contract for the L03_proxy app.

from __future__ import annotations

import json
from typing import Any

import requests

from .config import AppConfig


def require_non_empty_string(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")

    return cleaned


def decode_json_response(response: requests.Response) -> Any:
    try:
        return json.loads(response.content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Packages API response must be valid JSON.") from error


def require_json_object(payload: Any, action: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"Packages API {action} response must be a JSON object.")

    return payload


def require_confirmation(payload: dict[str, Any]) -> None:
    confirmation = payload.get("confirmation")
    if not isinstance(confirmation, str) or not confirmation.strip():
        raise ValueError("Packages API redirect response is missing confirmation.")


# This client wraps low-level communication with the external packages API.
class PackageApiClient:
    # This initializer stores application configuration needed by the API client.
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.session = requests.Session()

    def post_action(self, action: str, fields: dict[str, str]) -> dict[str, Any]:
        payload = {
            "apikey": self.config.ai_devs_api_key,
            "action": action,
            **fields,
        }

        response = self.session.post(
            self.config.proxy_api_url,
            json=payload,
            timeout=self.config.external_api_timeout_seconds,
        )
        response.raise_for_status()

        return require_json_object(decode_json_response(response), action)

    # This method will call the package status endpoint for one package ID.
    def check_package(self, package_id: str) -> dict[str, Any]:
        cleaned_package_id = require_non_empty_string(package_id, "package_id")

        return self.post_action(
            "check",
            {
                "packageid": cleaned_package_id,
            },
        )

    # This method will call the package redirect endpoint with operator-provided inputs.
    def redirect_package(
        self,
        package_id: str,
        destination: str,
        code: str,
    ) -> dict[str, Any]:
        cleaned_package_id = require_non_empty_string(package_id, "package_id")
        cleaned_destination = require_non_empty_string(destination, "destination")
        cleaned_code = require_non_empty_string(code, "code")

        payload = self.post_action(
            "redirect",
            {
                "packageid": cleaned_package_id,
                "destination": cleaned_destination,
                "code": cleaned_code,
            },
        )
        require_confirmation(payload)

        return payload
