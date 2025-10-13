"""Crawlee-based article fetching helper."""
from __future__ import annotations

import asyncio
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

    await crawler.run([url])

    if html is None:
        raise CrawleeFetchError("Crawler finished without returning content")
    return html


def fetch_with_crawlee_sync(url: str, config: CrawleeFetchConfig) -> str:
    """Synchronously fetch *url* using Crawlee/Playwright and return HTML."""
    try:
        return asyncio.run(_fetch_html_async(url, config))
    except CrawleeFetchError:
        raise
    except Exception as exc:  # pragma: no cover - unexpected runtime
        raise CrawleeFetchError(str(exc)) from exc


__all__ = ["CrawleeFetchConfig", "CrawleeFetchError", "fetch_with_crawlee_sync"]
