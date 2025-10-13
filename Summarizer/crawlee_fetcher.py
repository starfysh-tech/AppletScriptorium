"""Crawlee-based article fetching helper."""
from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from typing import Optional

from crawlee.crawlers import PlaywrightCrawler
from crawlee.crawlers import PlaywrightCrawlingContext


class CrawleeFetchError(RuntimeError):
    """Raised when Crawlee cannot return content for a URL."""


@dataclass(frozen=True)
class CrawleeFetchConfig:
    """Configuration for Crawlee fallback fetches."""

    timeout: float = 60.0
    headless: bool = True
    browser_type: str = "chromium"


async def _fetch_html_async(url: str, config: CrawleeFetchConfig) -> str:
    crawler = PlaywrightCrawler(
        headless=config.headless,
        browser_type=config.browser_type,
    )

    html: Optional[str] = None

    @crawler.router.default_handler
    async def handler(context: PlaywrightCrawlingContext) -> None:  # type: ignore[override]
        nonlocal html
        # Ensure any subsequent waits respect our timeout.
        context.page.set_default_timeout(config.timeout * 1000)
        await context.page.wait_for_load_state("networkidle")
        html = await context.page.content()

    try:
        async with asyncio.timeout(config.timeout):
            await crawler.run([url])
    except asyncio.TimeoutError as exc:
        raise CrawleeFetchError(f"timeout after {config.timeout}s") from exc

    if html is None:
        raise CrawleeFetchError("Crawler finished without returning content")
    return html


def fetch_with_crawlee_sync(url: str, config: CrawleeFetchConfig) -> str:
    """Synchronously fetch *url* using Crawlee/Playwright and return HTML."""
    try:
        with _LOOP_GUARD:
            return _LOOP.run_until_complete(_fetch_html_async(url, config))
    except CrawleeFetchError:
        raise
    except Exception as exc:  # pragma: no cover - unexpected runtime
        raise CrawleeFetchError(str(exc)) from exc


__all__ = ["CrawleeFetchConfig", "CrawleeFetchError", "fetch_with_crawlee_sync"]


_LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(_LOOP)
_LOOP_GUARD = threading.Lock()
