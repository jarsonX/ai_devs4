# Read-only HTTP client for the zmail mailbox API.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from src.apps.L9_mailbox.config import ExternalApiConfig, REQUEST_TIMEOUT_SECONDS


REDACTED = "***REDACTED***"
READ_ONLY_ACTIONS = frozenset({"help", "getInbox", "getThread", "getMessages", "search"})


# Store one decoded zmail response together with HTTP metadata.
@dataclass(frozen=True)
class ZmailResponse:
    status_code: int
    payload: Any
    text: str


# Build one zmail request payload and block unsupported or state-changing actions.
def build_zmail_payload(
    config: ExternalApiConfig,
    action: str,
    **params: Any,
) -> dict[str, Any]:
    if action not in READ_ONLY_ACTIONS:
        raise ValueError(f"Unsupported read-only zmail action: {action}.")

    return {
        "apikey": config.api_key,
        "action": action,
        **params,
    }


# Mask API keys before request payloads are written to reports or logs.
def mask_payload_for_storage(payload: dict[str, Any]) -> dict[str, Any]:
    masked_payload = dict(payload)
    if "apikey" in masked_payload:
        masked_payload["apikey"] = REDACTED
    return masked_payload


# Convert an HTTP response into a stable object with JSON fallback.
def build_zmail_response(response: requests.Response) -> ZmailResponse:
    try:
        payload = response.json()
    except requests.JSONDecodeError:
        payload = None

    return ZmailResponse(
        status_code=response.status_code,
        payload=payload,
        text=response.text,
    )


# Communicate with the read-only zmail mailbox actions.
class ZmailClient:
    # Store zmail configuration and an injectable HTTP session.
    def __init__(
        self,
        config: ExternalApiConfig,
        *,
        session: requests.Session | None = None,
        timeout_seconds: int = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self.config = config
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds

    # Send one approved zmail action and preserve the decoded response.
    def _post_action(self, action: str, **params: Any) -> ZmailResponse:
        response = self.session.post(
            self.config.zmail_url,
            json=build_zmail_payload(self.config, action, **params),
            timeout=self.timeout_seconds,
        )
        return build_zmail_response(response)

    # Fetch the API help contract.
    def help(self) -> ZmailResponse:
        return self._post_action("help")

    # List mailbox threads with optional pagination.
    def get_inbox(self, *, page: int = 1, per_page: int = 5) -> ZmailResponse:
        return self._post_action("getInbox", page=page, perPage=per_page)

    # Fetch message identifiers for one thread without message bodies.
    def get_thread(self, thread_id: int) -> ZmailResponse:
        return self._post_action("getThread", threadID=thread_id)

    # Fetch full message bodies by rowID, messageID, or a list of identifiers.
    def get_messages(self, ids: int | str | list[int | str]) -> ZmailResponse:
        return self._post_action("getMessages", ids=ids)

    # Search messages with Gmail-like query syntax and optional pagination.
    def search(self, query: str, *, page: int = 1, per_page: int = 5) -> ZmailResponse:
        return self._post_action("search", query=query, page=page, perPage=per_page)
