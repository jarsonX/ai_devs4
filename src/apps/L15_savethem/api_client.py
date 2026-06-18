# Guarded HTTP transport for discovery endpoints and optional verification.

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

import requests

from src.apps.L15_savethem.config import ExternalApiConfig
from src.apps.L15_savethem.models import ApiResponse, DiscoveredTool


REDACTED = "***REDACTED***"


# Define the small subset of requests.Session used by the client.
class SessionProtocol(Protocol):
    def post(self, *args: Any, **kwargs: Any) -> requests.Response:
        ...


# Store one masked request and its full response for logging.
@dataclass(frozen=True)
class LoggedExchange:
    request: dict[str, Any]
    response: ApiResponse


# Read a JSON response when possible while keeping text fallback.
def build_api_response(response: requests.Response) -> ApiResponse:
    try:
        payload = response.json()
    except requests.JSONDecodeError:
        payload = None
    return ApiResponse(
        status_code=response.status_code,
        payload=payload,
        text=response.text,
    )


# Remove the API key before preserving a request in runtime data.
def mask_payload(payload: dict[str, Any]) -> dict[str, Any]:
    masked_payload = dict(payload)
    if "apikey" in masked_payload:
        masked_payload["apikey"] = REDACTED
    return masked_payload


# Convert one raw tool dictionary into the internal tool shape.
def parse_discovered_tools(payload: Any) -> list[DiscoveredTool]:
    if not isinstance(payload, dict):
        return []
    raw_tools = payload.get("tools", [])
    if not isinstance(raw_tools, list):
        return []

    parsed_tools: list[DiscoveredTool] = []
    for raw_tool in raw_tools:
        if not isinstance(raw_tool, dict):
            continue
        name = str(raw_tool.get("name", "")).strip()
        url = str(raw_tool.get("url", "")).strip()
        description = str(raw_tool.get("description", "")).strip()
        parameter = str(raw_tool.get("parameter", "")).strip() or "query"
        if not name or not url:
            continue
        matched_keywords = raw_tool.get("matched_keywords", [])
        parsed_tools.append(
            DiscoveredTool(
                name=name,
                url=url,
                description=description,
                parameter=parameter,
                score=(
                    int(raw_tool["score"])
                    if isinstance(raw_tool.get("score"), int)
                    else None
                ),
                matched_keywords=tuple(
                    str(item).strip()
                    for item in matched_keywords
                    if str(item).strip()
                ),
            )
        )
    return parsed_tools


# Send discovery and verify requests through one reusable HTTP session.
class CourseApiClient:
    # Store external API config and injectable HTTP dependencies.
    def __init__(
        self,
        config: ExternalApiConfig,
        *,
        timeout_seconds: int,
        session: SessionProtocol | None = None,
    ) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    # Send one JSON request and return both masked request and parsed response.
    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
    ) -> LoggedExchange:
        response = self.session.post(
            url,
            json=payload,
            timeout=self.timeout_seconds,
        )
        return LoggedExchange(
            request=mask_payload(payload),
            response=build_api_response(response),
        )

    # Query the course toolsearch endpoint with one English prompt.
    def search_tools(self, query: str) -> LoggedExchange:
        payload = {
            "apikey": self.config.api_key,
            "query": query,
        }
        return self.post_json(self.config.toolsearch_url, payload)

    # Query one discovered tool by name and URL with the shared JSON contract.
    def query_tool(self, tool: DiscoveredTool, query: str) -> LoggedExchange:
        payload = {
            "apikey": self.config.api_key,
            "query": query,
        }
        return self.post_json(f"{self.config.hub_base_url}{tool.url}", payload)

    # Submit the final route only when explicit verification mode is enabled.
    def verify_answer(self, answer: list[str]) -> LoggedExchange:
        if not self.config.verify_url:
            raise ValueError("HUB_VERIFY_URL is missing.")
        payload = {
            "apikey": self.config.api_key,
            "task": self.config.task_name,
            "answer": answer,
        }
        return self.post_json(self.config.verify_url, payload)


# Build a compact JSON-safe summary from one endpoint payload for model context.
def build_payload_summary(payload: Any, *, max_chars: int) -> dict[str, Any]:
    if isinstance(payload, dict):
        summary: dict[str, Any] = {
            "keys": sorted(str(key) for key in payload.keys()),
        }
        if "code" in payload:
            summary["code"] = payload.get("code")
        if "message" in payload:
            summary["message"] = payload.get("message")
        if "query" in payload:
            summary["query"] = payload.get("query")
        if "text" in payload and isinstance(payload.get("text"), str):
            summary["text"] = truncate_text(str(payload["text"]), max_chars=max_chars)
        if "consumption" in payload:
            summary["consumption"] = payload.get("consumption")
        if "name" in payload:
            summary["name"] = payload.get("name")
        if "cityName" in payload:
            summary["cityName"] = payload.get("cityName")
        if "tools" in payload and isinstance(payload["tools"], list):
            summary["tools"] = [
                {
                    "name": item.get("name"),
                    "url": item.get("url"),
                    "description": item.get("description"),
                    "score": item.get("score"),
                }
                for item in payload["tools"]
                if isinstance(item, dict)
            ]
        if "notes" in payload and isinstance(payload["notes"], list):
            summary["notes"] = [
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "content": truncate_text(
                        str(item.get("content", "")),
                        max_chars=max_chars,
                    ),
                    "score": item.get("score"),
                }
                for item in payload["notes"]
                if isinstance(item, dict)
            ]
        if "map" in payload and isinstance(payload["map"], list):
            summary["map_rows"] = ["".join(str(cell) for cell in row) for row in payload["map"] if isinstance(row, list)]
        return summary

    if isinstance(payload, list):
        return {"items": payload[:10]}

    if payload is None:
        return {"payload": None}

    return {
        "payload_text": truncate_text(str(payload), max_chars=max_chars),
    }


# Keep model-visible snippets compact enough for iterative agent loops.
def truncate_text(value: str, *, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[: max_chars - 3]}..."

