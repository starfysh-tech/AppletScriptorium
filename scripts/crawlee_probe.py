"""Quick Crawlee smoke test."""
from __future__ import annotations

import argparse
import asyncio
from typing import List

from crawlee.crawlers import PlaywrightCrawler
from crawlee.crawlers import PlaywrightCrawlingContext


async def crawl_once(url: str, *, headless: bool, browser: str, timeout: float) -> str:
    crawler = PlaywrightCrawler(headless=headless, browser_type=browser)
    html_chunks: List[str] = []

    @crawler.router.default_handler
    async def handle(context: PlaywrightCrawlingContext) -> None:  # type: ignore[override]
        await context.page.wait_for_load_state("networkidle")
        html = await context.page.content()
        html_chunks.append(html)

    await crawler.run([url])
    if not html_chunks:
        raise RuntimeError("Crawler finished without returning content")
    return html_chunks[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch a URL via Crawlee Playwright crawler")
    parser.add_argument("url")
    parser.add_argument("--browser", default="chromium", choices=("chromium", "firefox", "webkit"))
    parser.add_argument("--headless", action="store_true", help="Run headless (default: headed for visibility)")
    parser.add_argument("--timeout", type=float, default=60.0, help="Navigation timeout in seconds")
    args = parser.parse_args()

    html = asyncio.run(crawl_once(args.url, headless=args.headless, browser=args.browser, timeout=args.timeout))
    print(f"Fetched {len(html)} bytes; preview:\n{html[:400]}")


if __name__ == "__main__":
    main()
