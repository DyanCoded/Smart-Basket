"""Abstract base scraper interface with async httpx lifecycle and rate-limiting.

All retailer-specific scrapers (Shoprite, Checkers, Pick n Pay, Woolworths Food,
SPAR) subclass BaseRetailerScraper to inherit polite rate-limiting, retry/backoff
semantics, and standardized RawScrapedItem output contracts.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

import httpx

from src.scrapers.models import RawScrapedItem

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "SmartBasketBot/2.0 (+https://github.com/DyanCoded/Smart-Basket; "
    "South African Grocery Price Intelligence)"
)
TRANSIENT_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}


class BaseRetailerScraper(ABC):
    """Abstract base class for South African national supermarket chain scrapers."""

    retailer_slug: str = ""
    base_url: str = ""

    def __init__(
        self,
        *,
        min_delay_seconds: float = 1.0,
        max_retries: int = 3,
        backoff_base_seconds: float = 0.5,
        timeout_seconds: float = 15.0,
        headers: Optional[dict[str, str]] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        if not self.retailer_slug:
            raise ValueError(
                f"{self.__class__.__name__} must define a non-empty 'retailer_slug'"
            )
        self.min_delay_seconds = max(0.0, min_delay_seconds)
        self.max_retries = max(1, max_retries)
        self.backoff_base_seconds = max(0.0, backoff_base_seconds)
        self.timeout_seconds = timeout_seconds
        self._transport = transport
        self._headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
            "Accept-Language": "en-ZA,en;q=0.9",
            **(headers or {}),
        }
        self._client: Optional[httpx.AsyncClient] = None
        self._last_request_ts: float = 0.0

    @property
    def client(self) -> httpx.AsyncClient:
        """Return active async httpx client, initializing lazily if needed."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url or "",
                headers=self._headers,
                timeout=httpx.Timeout(self.timeout_seconds),
                follow_redirects=True,
                transport=self._transport,
            )
        return self._client

    async def __aenter__(self) -> BaseRetailerScraper:
        _ = self.client
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying async httpx session cleanly."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    async def _throttle(self) -> None:
        """Enforce polite minimum delay between consecutive outbound requests."""
        if self.min_delay_seconds <= 0.0:
            return
        now = time.monotonic()
        elapsed = now - self._last_request_ts
        if self._last_request_ts > 0.0 and elapsed < self.min_delay_seconds:
            await asyncio.sleep(self.min_delay_seconds - elapsed)
        self._last_request_ts = time.monotonic()

    async def _fetch_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute an HTTP request with polite throttling and exponential backoff."""
        last_exc: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            await self._throttle()
            try:
                response = await self.client.request(method, url, **kwargs)
                if response.status_code not in TRANSIENT_HTTP_STATUS_CODES:
                    response.raise_for_status()
                    return response

                logger.warning(
                    "[%s] Transient HTTP %s on %s %s (attempt %d/%d)",
                    self.retailer_slug,
                    response.status_code,
                    method,
                    url,
                    attempt,
                    self.max_retries,
                )
                last_exc = httpx.HTTPStatusError(
                    f"Transient HTTP {response.status_code}",
                    request=response.request,
                    response=response,
                )
            except httpx.RequestError as exc:
                logger.warning(
                    "[%s] Network error on %s %s: %s (attempt %d/%d)",
                    self.retailer_slug,
                    method,
                    url,
                    exc,
                    attempt,
                    self.max_retries,
                )
                last_exc = exc

            if attempt < self.max_retries:
                backoff = self.backoff_base_seconds * (2 ** (attempt - 1))
                if backoff > 0:
                    await asyncio.sleep(backoff)

        assert last_exc is not None
        raise last_exc

    @abstractmethod
    async def scrape_catalog(self, query_terms: list[str]) -> list[RawScrapedItem]:
        """Extract raw product & pricing records for the given search queries.

        Args:
            query_terms: List of grocery search keywords (e.g. ['milk', 'bread']).

        Returns:
            List of unnormalized RawScrapedItem models.
        """


class PlaceholderFixtureScraper(BaseRetailerScraper):
    """PLACEHOLDER_ dry-run scraper using local fixture samples until live
    retailer adapters (#20-#24) are implemented.
    """

    def __init__(
        self,
        retailer_slug: str,
        sample_items: Optional[list[RawScrapedItem]] = None,
        **kwargs: Any,
    ) -> None:
        self.retailer_slug = retailer_slug.strip().lower()
        super().__init__(min_delay_seconds=0.0, **kwargs)
        self._sample_items = sample_items

    async def scrape_catalog(self, query_terms: list[str]) -> list[RawScrapedItem]:
        """Return filtered placeholder raw items simulating scraped storefront data."""
        items = (
            self._sample_items
            if self._sample_items is not None
            else self._default_placeholder_items()
        )
        if not query_terms:
            return list(items)
        lowered_terms = [t.strip().lower() for t in query_terms if t.strip()]
        if not lowered_terms:
            return list(items)
        return [
            item
            for item in items
            if any(term in item.raw_name.lower() for term in lowered_terms)
        ]

    def _default_placeholder_items(self) -> list[RawScrapedItem]:
        """PLACEHOLDER_ sample raw payloads exercising SA currency & unit formats."""
        price_map = {
            "shoprite": ("R 33.99", "R15.99 / ea", "R 58.99"),
            "checkers": ("R 31.99", "R17.99 / ea", "R 64.99"),
            "pick-n-pay": ("R 38.99", "R16.99 / ea", "2 FOR R109.98"),
            "spar": ("R 40.49", "R18.49 / ea", "R 66.49"),
            "woolworths-food": ("R 42.99", "R19.99 / ea", "R 62.99"),
        }
        milk_p, bread_p, eggs_p = price_map.get(
            self.retailer_slug, ("R 35.00", "R 17.50", "R 60.00")
        )
        return [
            RawScrapedItem(
                retailer_slug=self.retailer_slug,
                raw_name="Clover Full Cream Fresh Milk 2 Litre",
                raw_price=milk_p,
                brand="Clover",
                barcode="6001299011011",
                category_slug="dairy-eggs",
                raw_unit="2000ml",
                is_promotional=self.retailer_slug == "checkers",
                source_url=f"https://example.invalid/{self.retailer_slug}/milk-2l",
            ),
            RawScrapedItem(
                retailer_slug=self.retailer_slug,
                raw_name="Albany Superior Sliced White Bread 700g",
                raw_price=bread_p,
                brand="Albany",
                barcode="6001299011059",
                category_slug="bakery",
                raw_unit="700g",
                is_promotional=False,
                source_url=f"https://example.invalid/{self.retailer_slug}/white-bread",
            ),
            RawScrapedItem(
                retailer_slug=self.retailer_slug,
                raw_name="Farmer Brown Large Eggs 18pk",
                raw_price=eggs_p,
                brand="Farmer Brown",
                barcode="6001299011028",
                category_slug="dairy-eggs",
                raw_unit="18 pack",
                is_promotional=self.retailer_slug == "pick-n-pay",
                source_url=f"https://example.invalid/{self.retailer_slug}/eggs-18pk",
            ),
        ]
