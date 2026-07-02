# Data models shared by the L20 foodwarehouse workflow.

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


FLAG_PREFIX = "".join(chr(value) for value in (70, 76, 71))
FLAG_PATTERN = re.compile(r"\{" + FLAG_PREFIX + r":[^}]+\}")


# Store one decoded or raw Hub response.
@dataclass(frozen=True)
class ApiResponse:
    status_code: int
    payload: Any | None
    text: str


# Store one masked request and its full response for runtime data.
@dataclass(frozen=True)
class LoggedExchange:
    sequence: int
    action: str
    request: dict[str, Any]
    response: ApiResponse

    # Convert the exchange into JSON-safe output.
    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "action": self.action,
            "request": self.request,
            "response": {
                "status_code": self.response.status_code,
                "payload": self.response.payload,
                "text": self.response.text,
                "flag_found": response_contains_flag(self.response),
            },
        }


# Store one local city demand loaded from food4cities.json.
@dataclass(frozen=True)
class CityDemand:
    city: str
    items: dict[str, int]


# Store all data needed to create and fill one Hub order.
@dataclass(frozen=True)
class OrderPlan:
    city: str
    title: str
    creator_id: int
    destination: str
    signature: str
    items: dict[str, int]


# Return whether one response contains a FLAG anywhere in its visible content.
def response_contains_flag(response: ApiResponse) -> bool:
    haystack = response.text
    if response.payload is not None:
        haystack = f"{haystack}\n{json.dumps(response.payload, ensure_ascii=False)}"
    return FLAG_PATTERN.search(haystack) is not None
