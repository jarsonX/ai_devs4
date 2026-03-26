from __future__ import annotations

import json
from typing import Any

import requests

from .config import AppConfig


def decode_json_response(response: requests.Response) -> Any:
    return json.loads(response.content.decode("utf-8"))


def parse_access_level(payload: Any) -> int:
    if not isinstance(payload, dict):
        raise ValueError("Access level response mut be a JSON object.")
    
    value = payload.get("accessLevel")
    if value is None:
        raise ValueError(f"Missing accessLevel in payload: {payload!r}")
    
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid accessLevel value: {value!r}") from error
    

class Edu1ApiClient:
    def __init__(self, config: AppConfig, timeout: int = 30) -> None:
        self.config = config
        self.timeout = timeout
        self.session = requests.Session()

    def get_access_level(self, name: str, surname: str, birth_year: int) -> int:
        payload = {
            "apikey": self.config.ai_devs_api_key,
            "name": name,
            "surname": surname,
            "birthYear": birth_year
        }

        response = self.session.post(
            self.config.access_level_api_url,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()

        return parse_access_level(decode_json_response(response))