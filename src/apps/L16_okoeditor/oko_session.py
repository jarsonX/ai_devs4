# Authenticated read-only OKO web session handling.

from __future__ import annotations

from urllib.parse import urljoin

import requests

from src.apps.L16_okoeditor.config import OkoWebConfig


LIST_PAGE_PATHS = {
    "incydenty": "",
    "zadania": "zadania",
    "notatki": "notatki",
    "uzytkownicy": "uzytkownicy",
}


# Keep read-only web access bounded and explicit.
class OkoWebClient:
    # Store one logged-in session and the page-fetch guard.
    def __init__(
        self,
        config: OkoWebConfig,
        *,
        timeout_seconds: int,
        max_page_fetches: int,
    ) -> None:
        self._config = config
        self._timeout_seconds = timeout_seconds
        self._max_page_fetches = max_page_fetches
        self._page_fetch_count = 0
        self._session = requests.Session()
        self._logged_in = False

    # Log in only for state inspection and confirm that the panel is visible.
    def login(self) -> None:
        response = self._session.post(
            self._config.base_url,
            data={
                "action": "login",
                "login": self._config.operator_login,
                "password": self._config.operator_password,
                "access_key": self._config.access_key,
            },
            timeout=self._timeout_seconds,
            allow_redirects=True,
        )
        response.raise_for_status()

        panel_response = self._session.get(self._config.base_url, timeout=self._timeout_seconds)
        panel_response.raise_for_status()
        if "Centrum operacyjne OKO" not in panel_response.text:
            raise ValueError("OKO login succeeded at HTTP level but the control-center panel is not visible.")
        self._logged_in = True

    # Log out from the web session after read-only inspection finishes.
    def logout(self) -> None:
        if not self._logged_in:
            return
        response = self._session.post(
            self._config.base_url,
            data={"action": "logout"},
            timeout=self._timeout_seconds,
            allow_redirects=True,
        )
        response.raise_for_status()
        self._logged_in = False

    # Fetch one list page HTML by page name.
    def fetch_list_html(self, page: str) -> str:
        self._ensure_logged_in()
        relative_path = LIST_PAGE_PATHS[page]
        url = urljoin(self._config.base_url, relative_path)
        return self._fetch_html(url)

    # Fetch one detail page HTML by page name and record id.
    def fetch_detail_html(self, page: str, record_id: str) -> str:
        self._ensure_logged_in()
        url = urljoin(self._config.base_url, f"{page}/{record_id}")
        return self._fetch_html(url)

    # Build the public URL used later by parsers and reports.
    def build_detail_url(self, page: str, record_id: str) -> str:
        return urljoin(self._config.base_url, f"{page}/{record_id}")

    # Return how many page fetches were used in the current session.
    def page_fetch_count(self) -> int:
        return self._page_fetch_count

    # Enforce the inspection-only fetch guard before each request.
    def _fetch_html(self, url: str) -> str:
        self._page_fetch_count += 1
        if self._page_fetch_count > self._max_page_fetches:
            raise ValueError("The OKO page fetch guard was exceeded.")
        response = self._session.get(url, timeout=self._timeout_seconds, allow_redirects=True)
        response.raise_for_status()
        return response.text

    # Refuse page reads before an authenticated session exists.
    def _ensure_logged_in(self) -> None:
        if not self._logged_in:
            raise ValueError("OKO web session is not logged in.")
