"""Async Playwright headless Chromium fetcher for JS-rendered SA supermarket sites.

Provides PlaywrightFetcher (an async context manager built on playwright.async_api)
with South African locale (`en-ZA`, `Africa/Johannesburg`), XHR/Fetch JSON response
interception, rendered DOM HTML extraction, and respectful hard-block detection
(403/CAPTCHA/WAF halts immediately with a clear warning and zero circumvention).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

logger = logging.getLogger(__name__)

DEFAULT_SA_DESKTOP_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)

DEFAULT_SA_MOBILE_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Mobile Safari/537.36"
)

DEFAULT_LOCALE = "en-ZA"
DEFAULT_TIMEZONE = "Africa/Johannesburg"

HARD_BLOCK_STATUS_CODES = {403, 451}
HARD_BLOCK_MARKERS: tuple[str, ...] = (
    "cf-browser-verification",
    "attention required! | cloudflare",
    "verify you are human",
    "cf-turnstile",
    "challenges.cloudflare.com",
    "request unsuccessful. incapsula",
    "/_incapsula_resource",
    "g-recaptcha",
    "h-captcha",
    "access denied",
)


class PlaywrightUnavailableError(RuntimeError):
    """Raised when the playwright package or Chromium browser binary is missing."""


@dataclass
class PlaywrightPageResult:
    """Result captured by PlaywrightFetcher for a single storefront navigation."""

    url: str
    status_code: int
    html: str
    intercepted_json: list[tuple[str, Any]] = field(default_factory=list)
    blocked: bool = False
    block_reason: Optional[str] = None


def is_hard_block_response(
    status_code: int, html_body: str
) -> tuple[bool, Optional[str]]:
    """Detect HTTP 403/451 or CAPTCHA/WAF gates so scrapers halt respectfully."""
    if status_code in HARD_BLOCK_STATUS_CODES:
        return (True, f"HTTP {status_code} access control block")
    sample = html_body[:6000].lower()
    for marker in HARD_BLOCK_MARKERS:
        if marker in sample:
            return (True, f"Anti-bot/CAPTCHA challenge marker ({marker})")
    return (False, None)


class PlaywrightFetcher:
    """Async headless/headed Chromium fetcher with XHR JSON capture & DOM extraction."""

    def __init__(
        self,
        *,
        headless: bool = True,
        mobile: bool = False,
        locale: str = DEFAULT_LOCALE,
        timezone_id: str = DEFAULT_TIMEZONE,
        user_agent: Optional[str] = None,
        navigation_timeout_ms: int = 25000,
        network_idle_timeout_ms: int = 8000,
    ) -> None:
        self.headless = headless
        self.mobile = mobile
        self.locale = locale
        self.timezone_id = timezone_id
        self.user_agent = user_agent or (
            DEFAULT_SA_MOBILE_USER_AGENT if mobile else DEFAULT_SA_DESKTOP_USER_AGENT
        )
        self.viewport = (
            {"width": 390, "height": 844} if mobile else {"width": 1366, "height": 900}
        )
        self.navigation_timeout_ms = max(1000, navigation_timeout_ms)
        self.network_idle_timeout_ms = max(500, network_idle_timeout_ms)

        self._playwright_cm: Any = None
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None

    async def __aenter__(self) -> PlaywrightFetcher:
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    async def start(self) -> None:
        """Start Playwright and launch Chromium with en-ZA locale settings."""
        if self._context is not None:
            return

        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise PlaywrightUnavailableError(
                "Playwright is not installed. Run: "
                "pip install playwright && playwright install chromium"
            ) from exc

        try:
            self._playwright_cm = async_playwright()
            self._playwright = await self._playwright_cm.start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless
            )
            self._context = await self._browser.new_context(
                user_agent=self.user_agent,
                locale=self.locale,
                timezone_id=self.timezone_id,
                viewport=self.viewport,
                is_mobile=self.mobile,
                extra_http_headers={"Accept-Language": f"{self.locale},en;q=0.9"},
            )
        except Exception as exc:
            await self.close()
            msg = str(exc)
            if "executable doesn't exist" in msg.lower() or "chromium" in msg.lower():
                raise PlaywrightUnavailableError(
                    "Chromium browser binary is not installed for Playwright. "
                    "Run: playwright install chromium"
                ) from exc
            raise PlaywrightUnavailableError(
                f"Failed to start Playwright Chromium browser: {exc}"
            ) from exc

    async def close(self) -> None:
        """Tear down Chromium context, browser process, and Playwright driver."""
        for resource, method in (
            (self._context, "close"),
            (self._browser, "close"),
            (self._playwright, "stop"),
        ):
            if resource is not None:
                try:
                    await getattr(resource, method)()
                except Exception:  # noqa: BLE001
                    logger.debug("Ignoring error during Playwright teardown")
        self._context = None
        self._browser = None
        self._playwright = None
        self._playwright_cm = None

    async def fetch_page(
        self,
        url: str,
        *,
        wait_selector: Optional[str] = None,
        json_url_patterns: Optional[Sequence[str]] = None,
    ) -> PlaywrightPageResult:
        """Navigate to a URL, capture matching XHR/Fetch JSON, and read DOM."""
        if self._context is None:
            await self.start()

        assert self._context is not None
        page = await self._context.new_page()
        intercepted: list[tuple[str, Any]] = []
        patterns_lower = [p.lower() for p in (json_url_patterns or ())]

        async def _handle_response(response: Any) -> None:
            try:
                content_type = (response.headers or {}).get("content-type", "").lower()
                if "json" not in content_type:
                    return
                resp_url = str(response.url)
                if patterns_lower and not any(
                    pat in resp_url.lower() for pat in patterns_lower
                ):
                    return
                if response.status >= 400:
                    return
                payload = await response.json()
                intercepted.append((resp_url, payload))
            except Exception:  # noqa: BLE001
                # Ignore non-JSON or aborted background responses
                return

        page.on("response", _handle_response)

        try:
            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=self.navigation_timeout_ms,
            )
            status_code = response.status if response is not None else 200

            if status_code in HARD_BLOCK_STATUS_CODES:
                html_body = await page.content()
                return PlaywrightPageResult(
                    url=page.url,
                    status_code=status_code,
                    html=html_body,
                    intercepted_json=intercepted,
                    blocked=True,
                    block_reason=f"HTTP {status_code} access control block",
                )

            if wait_selector:
                try:
                    await page.wait_for_selector(
                        wait_selector,
                        timeout=self.network_idle_timeout_ms,
                    )
                except Exception:  # noqa: BLE001
                    logger.debug(
                        "Selector %r did not appear within %dms on %s",
                        wait_selector,
                        self.network_idle_timeout_ms,
                        url,
                    )

            try:
                await page.wait_for_load_state(
                    "networkidle",
                    timeout=self.network_idle_timeout_ms,
                )
            except Exception:  # noqa: BLE001
                logger.debug("Network-idle wait timed out on %s; reading DOM", url)

            html_body = await page.content()
            blocked, reason = is_hard_block_response(status_code, html_body)
            return PlaywrightPageResult(
                url=page.url,
                status_code=status_code,
                html=html_body,
                intercepted_json=intercepted,
                blocked=blocked,
                block_reason=reason,
            )
        finally:
            await page.close()
