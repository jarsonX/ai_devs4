# Deterministic Playwright login, control, observation, and activation tools.

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlsplit

from playwright.sync_api import Browser, BrowserContext, Locator, Page, Playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from src.apps.L25_timetravel.config import BrowserConfig, RuntimeConfig
from src.apps.L25_timetravel.coordination import CoordinationStore
from src.apps.L25_timetravel.models import FrontendObservation, MachineSnapshot, TravelLeg


PREVIEW_HOST = "hub.ag3nts.org"
LOGIN_HOST = "cart.easy.tools"
IDENTITY_HOST = "id.easy.tools"
ALLOWED_MAIN_FRAME_HOSTS = frozenset({PREVIEW_HOST, LOGIN_HOST, IDENTITY_HOST})
MONTHS = {
    "STYCZNIA": 1,
    "LUTEGO": 2,
    "MARCA": 3,
    "KWIETNIA": 4,
    "MAJA": 5,
    "CZERWCA": 6,
    "LIPCA": 7,
    "SIERPNIA": 8,
    "WRZEŚNIA": 9,
    "PAŹDZIERNIKA": 10,
    "LISTOPADA": 11,
    "GRUDNIA": 12,
}


# Report a deterministic browser contract failure before risky interaction.
class BrowserToolError(RuntimeError):
    pass


# Mark a post-click timeout as ambiguous so no caller can retry blindly.
class ActivationAmbiguousError(BrowserToolError):
    pass


# Return the first visible locator from a narrow deterministic candidate list.
def first_visible(candidates: list[Locator]) -> Locator | None:
    for candidate in candidates:
        if candidate.count() > 0 and candidate.first.is_visible():
            return candidate.first
    return None


# Control one fresh authenticated preview context and no arbitrary page.
class TimetravelBrowser:
    # Store configuration without opening a browser or reading credentials aloud.
    def __init__(self, config: BrowserConfig, runtime: RuntimeConfig) -> None:
        self.config = config
        self.runtime = runtime
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self._used_activation_ids: set[str] = set()

    # Launch Edge, authenticate through approved hosts, and require the preview.
    def open(self) -> None:
        parsed = urlsplit(self.config.preview_url)
        if parsed.scheme != "https" or parsed.hostname != PREVIEW_HOST:
            raise BrowserToolError("Preview URL is outside the approved HTTPS host.")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            channel=self.config.channel,
            headless=self.config.headless,
        )
        self.context = self.browser.new_context(
            viewport={"width": 1440, "height": 1200},
            ignore_https_errors=False,
        )
        self.page = self.context.new_page()
        self.page.set_default_timeout(self.runtime.request_timeout_seconds * 1000)
        self.page.goto(
            self.config.preview_url,
            wait_until="domcontentloaded",
            timeout=self.runtime.request_timeout_seconds * 1000,
        )
        self._validate_location()
        self._authenticate_if_needed()
        self.page.wait_for_timeout(int(self.runtime.post_write_settle_seconds * 1000))
        self._validate_location(expected_path="/timetravel_preview")

    # Close the ephemeral context without exporting reusable auth state.
    def close(self) -> None:
        if self.context is not None:
            self.context.close()
        if self.browser is not None:
            self.browser.close()
        if self.playwright is not None:
            self.playwright.stop()
        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None

    # Return the active preview page or fail before a tool action.
    def _page(self) -> Page:
        if self.page is None:
            raise BrowserToolError("Browser session is not open.")
        return self.page

    # Reject any unexpected main-frame host or preview path.
    def _validate_location(self, expected_path: str | None = None) -> None:
        page = self._page()
        parsed = urlsplit(page.url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_MAIN_FRAME_HOSTS:
            raise BrowserToolError(
                f"Unexpected main-frame location: {parsed.scheme}://{parsed.hostname}{parsed.path}."
            )
        if expected_path is not None and (
            parsed.hostname != PREVIEW_HOST or parsed.path != expected_path
        ):
            raise BrowserToolError(
                f"Expected Hub path {expected_path!r}, reached {parsed.path!r}."
            )

    # Select password login explicitly and keep credential values inside this helper.
    def _authenticate_if_needed(self) -> None:
        page = self._page()
        parsed = urlsplit(page.url)
        if parsed.hostname == PREVIEW_HOST:
            return
        if parsed.hostname == LOGIN_HOST and parsed.path == "/brave/login":
            login_links: list[Locator] = []
            for candidate in page.locator("a").all():
                href = candidate.get_attribute("href")
                if not href or not candidate.is_visible():
                    continue
                target = urlsplit(urljoin(page.url, href))
                if (
                    target.hostname == LOGIN_HOST
                    and target.path == "/login"
                    and "redirect" in parse_qs(target.query)
                ):
                    login_links.append(candidate)
            if len(login_links) != 1:
                raise BrowserToolError("Protected-page login link was not found uniquely.")
            login_links[0].click()
            page.wait_for_load_state("domcontentloaded")
            self._validate_location()
        password_mode = first_visible(
            [
                page.get_by_role("button", name="Hasło", exact=True),
                page.locator('button:has-text("Hasło")'),
            ]
        )
        if password_mode is None:
            raise BrowserToolError("Easytools password mode control was not found.")
        password_mode.click()
        page.wait_for_timeout(300)
        email = first_visible(
            [page.locator('input[type="email"]'), page.locator('input[name="email"]')]
        )
        password = first_visible(
            [
                page.locator('input[type="password"]'),
                page.locator('input[name="password"]'),
            ]
        )
        submit = first_visible(
            [
                page.locator('button[type="submit"]'),
                page.get_by_role("button", name="Zaloguj się", exact=True),
            ]
        )
        if email is None or password is None or submit is None:
            raise BrowserToolError("Easytools password form is incomplete.")
        email.fill(self.config.email)
        password.fill(self.config.password)
        submit.click()
        try:
            page.wait_for_url(
                lambda value: urlsplit(value).hostname == PREVIEW_HOST,
                timeout=self.runtime.request_timeout_seconds * 1000,
                wait_until="domcontentloaded",
            )
        except PlaywrightTimeoutError as error:
            raise BrowserToolError("Easytools login did not return to the Hub preview.") from error
        self._validate_location(expected_path="/timetravel_preview")

    # Read one complete typed frontend observation from stable DOM state.
    def snapshot(self) -> FrontendObservation:
        page = self._page()
        self._validate_location(expected_path="/timetravel_preview")
        raw = page.evaluate(
            """
            () => {
              const byId = (id) => document.getElementById(id);
              const activeMode = document.querySelector('.imode-dot.lit');
              const battery = byId('batteryIndicator');
              const orb = byId('orb');
              return {
                PTA: byId('portA')?.getAttribute('aria-checked') === 'true',
                PTB: byId('portB')?.getAttribute('aria-checked') === 'true',
                mode: byId('mainSwitch')?.getAttribute('aria-checked') === 'true'
                  ? 'active' : 'standby',
                PWR: Number(byId('pwrSlider')?.value ?? -1),
                day: document.querySelector('.field-day')?.value ?? null,
                month: document.querySelector('.field-month')?.value ?? null,
                year: document.querySelector('.field-year')?.value ?? null,
                currentDate: byId('currentDateVal')?.textContent?.trim() ?? null,
                fluxDensity: Number((byId('fluxPct')?.textContent ?? '').replace('%', '')),
                syncRatio: Number((byId('syncPct')?.textContent ?? '').replace('%', '')) / 100,
                conditionStable: byId('condLabel')?.classList.contains('stable') ?? false,
                internalMode: activeMode ? Number(activeMode.getAttribute('data-m')) : null,
                chargedCells: document.querySelectorAll(
                  '#batteryIndicator .battery-cell.charged'
                ).length,
                totalCells: document.querySelectorAll(
                  '#batteryIndicator .battery-cell'
                ).length,
                orbPowered: orb?.classList.contains('powered') ?? false,
                orbDanger: orb?.classList.contains('danger') ?? true,
                sameDate: byId('sameDateMsg')?.classList.contains('visible') ?? false,
                toast: byId('deviceToast')?.classList.contains('visible')
                  ? byId('deviceToast')?.textContent?.trim() : null,
                flag: byId('flagOverlay')?.classList.contains('visible')
                  ? byId('flagText')?.textContent?.trim() : null,
                batteryClass: battery?.className ?? ''
              };
            }
            """
        )
        day_text = str(raw.get("day") or "")
        year_text = str(raw.get("year") or "")
        day = int(day_text) if day_text.isdigit() and int(day_text) > 0 else None
        year = int(year_text) if year_text.isdigit() and int(year_text) > 0 else None
        month = MONTHS.get(str(raw.get("month") or "").upper())
        machine = MachineSnapshot(
            currentDate=str(raw["currentDate"]),
            day=day,
            month=month,
            year=year,
            syncRatio=float(raw["syncRatio"]),
            stabilization=None,
            condition="stable" if raw["conditionStable"] else "unstable",
            fluxDensity=int(raw["fluxDensity"]),
            batteryStatus=f"{int(raw['chargedCells'])}/{int(raw['totalCells'])}",
            PTA=bool(raw["PTA"]),
            PTB=bool(raw["PTB"]),
            PWR=int(raw["PWR"]),
            mode=raw["mode"],
            internalMode=int(raw["internalMode"]),
            captured_at=datetime.now(UTC),
        )
        orb_powered = bool(raw["orbPowered"])
        orb_danger = bool(raw["orbDanger"])
        return FrontendObservation(
            machine=machine,
            orb_powered=orb_powered,
            orb_danger=orb_danger,
            activation_ready=orb_powered and not orb_danger,
            same_date_warning=bool(raw["sameDate"]),
            toast=raw.get("toast") or None,
            flag=raw.get("flag") or None,
        )

    # Set both PT switches and verify server-persisted DOM state after polling.
    def set_ports(self, pta: bool, ptb: bool) -> FrontendObservation:
        page = self._page()
        for selector, expected in (("#portA", pta), ("#portB", ptb)):
            locator = page.locator(selector)
            current = locator.get_attribute("aria-checked") == "true"
            if current != expected:
                locator.click()
                page.wait_for_timeout(250)
                if (locator.get_attribute("aria-checked") == "true") != expected:
                    raise BrowserToolError(f"{selector} did not change to {expected}.")
        page.wait_for_timeout(int(self.runtime.post_write_settle_seconds * 1000))
        observed = self.snapshot()
        if observed.machine.PTA != pta or observed.machine.PTB != ptb:
            raise BrowserToolError("PT state did not persist after the server poll.")
        return observed

    # Set PWR through a normal range interaction and verify persistence.
    def set_power(self, value: int) -> FrontendObservation:
        if not 0 <= value <= 100:
            raise ValueError("PWR must be between 0 and 100.")
        page = self._page()
        slider = page.locator("#pwrSlider")
        slider.fill(str(value))
        slider.press("Tab")
        page.wait_for_timeout(int(self.runtime.post_write_settle_seconds * 1000))
        observed = self.snapshot()
        if observed.machine.PWR != value:
            raise BrowserToolError("PWR did not persist after the server poll.")
        return observed

    # Switch standby or active and verify the server-persisted DOM state.
    def set_mode(self, mode: str) -> FrontendObservation:
        if mode not in {"standby", "active"}:
            raise ValueError("Mode must be standby or active.")
        page = self._page()
        switch = page.locator("#mainSwitch")
        current = "active" if switch.get_attribute("aria-checked") == "true" else "standby"
        if current != mode:
            switch.click()
        page.wait_for_timeout(int(self.runtime.post_write_settle_seconds * 1000))
        observed = self.snapshot()
        if observed.machine.mode != mode:
            raise BrowserToolError(f"Mode did not persist as {mode}.")
        return observed

    # Poll the visible preview until every activation condition matches one leg.
    def wait_until_ready(self, leg: TravelLeg) -> FrontendObservation:
        deadline = time.monotonic() + self.runtime.mode_wait_timeout_seconds
        last: FrontendObservation | None = None
        while time.monotonic() < deadline:
            last = self.snapshot()
            machine = last.machine
            if (
                machine.target() == leg.target
                and machine.PTA == leg.pta
                and machine.PTB == leg.ptb
                and machine.PWR == leg.pwr
                and machine.mode == "active"
                and machine.internalMode == leg.required_internal_mode
                and machine.fluxDensity == 100
                and machine.condition == "stable"
                and last.activation_ready
                and not last.same_date_warning
            ):
                return last
            time.sleep(self.runtime.poll_interval_seconds)
        detail = last.model_dump(mode="json") if last is not None else None
        rendered = json.dumps(detail, ensure_ascii=False)
        raise BrowserToolError(f"Frontend readiness timeout: {rendered}")

    # Consume one lease and click the activation sphere exactly once.
    def activate_once(
        self,
        store: CoordinationStore,
        lease_id: str,
        run_id: str,
        state_version: int,
        config_digest: str,
        leg: TravelLeg,
        *,
        evidence_path: Path | None = None,
    ) -> dict[str, Any]:
        if lease_id in self._used_activation_ids:
            raise BrowserToolError("Activation lease was already used in this browser session.")
        ready = self.snapshot()
        machine = ready.machine
        if not (
            machine.target() == leg.target
            and machine.PTA == leg.pta
            and machine.PTB == leg.ptb
            and machine.PWR == leg.pwr
            and machine.mode == "active"
            and machine.internalMode == leg.required_internal_mode
            and machine.fluxDensity == 100
            and machine.condition == "stable"
            and ready.activation_ready
            and not ready.same_date_warning
        ):
            raise BrowserToolError("Activation readiness changed before the click.")
        store.consume_activation_lease(lease_id, run_id, state_version, config_digest)
        self._used_activation_ids.add(lease_id)
        page = self._page()
        try:
            with page.expect_response(
                lambda response: (
                    urlsplit(response.url).path == "/verify"
                    and response.request.method == "POST"
                ),
                timeout=self.runtime.request_timeout_seconds * 1000,
            ) as response_info:
                page.locator("#orb").click()
            response = response_info.value
            payload = response.json()
        except PlaywrightTimeoutError as error:
            raise ActivationAmbiguousError(
                "Activation was clicked but no /verify response was observed."
            ) from error
        except Exception as error:
            raise ActivationAmbiguousError(
                "Activation was clicked but its response could not be validated."
            ) from error
        if evidence_path is not None:
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            page.wait_for_timeout(500)
            page.screenshot(path=str(evidence_path), full_page=True)
        if not isinstance(payload, dict):
            raise BrowserToolError("Activation response is not a JSON object.")
        if payload.get("code") != 13:
            raise BrowserToolError(str(payload.get("message") or "Activation was rejected."))
        return payload
