"""Crawlee-based article fetching helper."""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
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
        max_request_retries=0,  # Disable retries; handled by article_fetcher
        max_requests_per_crawl=1,  # Only fetch the single URL
        max_crawl_depth=0,  # Don't follow links
    )

    html: Optional[str] = None
    error: Optional[Exception] = None

    @crawler.router.default_handler
    async def handler(context: PlaywrightCrawlingContext) -> None:  # type: ignore[override]
        nonlocal html, error
        try:
            # Set page timeout for all operations
            context.page.set_default_timeout(config.timeout * 1000)

            # Wait for initial load (more lenient than networkidle)
            await context.page.wait_for_load_state("load", timeout=config.timeout * 1000)

            # Check for Cloudflare challenge and wait for it to complete
            await _wait_for_cloudflare_challenge(context.page, config.timeout)

            # Additional wait for dynamic content to stabilize
            await asyncio.sleep(2)

            html = await context.page.content()
        except Exception as exc:
            error = exc

    try:
        async with asyncio.timeout(config.timeout + 5):
            await crawler.run([url])
    except asyncio.TimeoutError as exc:
        raise CrawleeFetchError(f"timeout after {config.timeout}s") from exc
    finally:
        # Ensure browser and resources are properly cleaned up
        try:
            if hasattr(crawler, '_browser_pool') and crawler._browser_pool:
                await crawler._browser_pool.destroy()
        except Exception:
            pass

    if error is not None:
        raise CrawleeFetchError(f"page handler error: {error}") from error

    if html is None:
        raise CrawleeFetchError("Crawler finished without returning content")
    return html


async def _wait_for_cloudflare_challenge(page, timeout: float) -> None:
    """Wait for Cloudflare challenge to complete if detected."""
    try:
        # Check for common Cloudflare challenge indicators
        cloudflare_selectors = [
            "div.cf-browser-verification",
            "div#cf-wrapper",
            "div.cf-error-title",
            "#challenge-running",
        ]

        for selector in cloudflare_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    # Cloudflare challenge detected, wait for it to disappear
                    await page.wait_for_selector(selector, state="hidden", timeout=timeout * 1000)
                    # Extra wait for redirect/reload after challenge
                    await asyncio.sleep(3)
                    break
            except Exception:
                # Selector not found or timeout, continue
                pass
    except Exception:
        # If challenge detection fails, continue anyway
        pass


def fetch_with_crawlee_sync(url: str, config: CrawleeFetchConfig) -> str:
    """Synchronously fetch *url* using Crawlee/Playwright and return HTML."""
    try:
        # Run crawler in subprocess for complete isolation
        # This prevents event loop conflicts when called multiple times sequentially
        with _SYNC_GUARD:
            return _fetch_in_subprocess(url, config)
    except CrawleeFetchError:
        raise
    except Exception as exc:  # pragma: no cover - unexpected runtime
        raise CrawleeFetchError(str(exc)) from exc


def _fetch_in_subprocess(url: str, config: CrawleeFetchConfig) -> str:
    """Run the crawler in a subprocess to avoid event loop conflicts."""
    script = f"""
import asyncio
import json
import sys
from crawlee.crawlers import PlaywrightCrawler
from crawlee.crawlers import PlaywrightCrawlingContext

async def fetch():
    crawler = PlaywrightCrawler(
        headless={config.headless},
        browser_type="{config.browser_type}",
        max_request_retries=0,
        max_requests_per_crawl=1,
        max_crawl_depth=0,
    )
    html = None
    error = None

    @crawler.router.default_handler
    async def handler(context: PlaywrightCrawlingContext):
        nonlocal html, error
        try:
            context.page.set_default_timeout({config.timeout * 1000})
            await context.page.wait_for_load_state("load", timeout={config.timeout * 1000})

            # Check for Cloudflare and PerimeterX challenges
            challenge_selectors = [
                "div.cf-browser-verification",
                "div#cf-wrapper",
                "div.cf-error-title",
                "#challenge-running",
                "#px-captcha",  # PerimeterX
                "iframe[src*='perimeterx']",  # PerimeterX iframe
            ]
            challenge_detected = False
            for selector in challenge_selectors:
                try:
                    element = await context.page.query_selector(selector)
                    if element:
                        challenge_detected = True
                        await context.page.wait_for_selector(selector, state="hidden", timeout={config.timeout * 1000})
                        await asyncio.sleep(5)  # Longer wait for challenge completion
                        break
                except Exception:
                    pass

            # Additional wait for dynamic content/challenges
            if challenge_detected:
                await asyncio.sleep(3)
            else:
                await asyncio.sleep(2)
            html = await context.page.content()
        except Exception as exc:
            error = str(exc)

    try:
        async with asyncio.timeout({config.timeout + 5}):
            await crawler.run([{json.dumps(url)}])
    except asyncio.TimeoutError:
        error = "timeout after {config.timeout}s"
    finally:
        try:
            if hasattr(crawler, '_browser_pool') and crawler._browser_pool:
                await crawler._browser_pool.destroy()
        except Exception:
            pass

    if error:
        print(json.dumps({{"error": error}}), file=sys.stderr)
        sys.exit(1)
    if html is None:
        print(json.dumps({{"error": "Crawler finished without returning content"}}), file=sys.stderr)
        sys.exit(1)

    print(json.dumps({{"html": html}}))

asyncio.run(fetch())
"""

    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=config.timeout + 10,
            check=False,
        )

        if result.returncode != 0:
            try:
                error_data = json.loads(result.stderr)
                raise CrawleeFetchError(error_data.get("error", "Unknown error"))
            except json.JSONDecodeError:
                # Capture more stderr for debugging
                stderr_lines = result.stderr.strip().split('\n')
                # Get last 10 lines which usually contain the actual error
                error_summary = '\n'.join(stderr_lines[-10:]) if len(stderr_lines) > 10 else result.stderr
                raise CrawleeFetchError(f"subprocess failed: {error_summary[:1000]}")

        try:
            output_data = json.loads(result.stdout)
            return output_data["html"]
        except (json.JSONDecodeError, KeyError) as exc:
            raise CrawleeFetchError(f"invalid subprocess output: {exc}")

    except subprocess.TimeoutExpired as exc:
        raise CrawleeFetchError(f"subprocess timeout after {config.timeout}s") from exc
    except Exception as exc:
        if isinstance(exc, CrawleeFetchError):
            raise
        raise CrawleeFetchError(f"subprocess error: {exc}") from exc


__all__ = ["CrawleeFetchConfig", "CrawleeFetchError", "fetch_with_crawlee_sync"]


# Threading lock to prevent concurrent crawls from interfering
_SYNC_GUARD = threading.Lock()
