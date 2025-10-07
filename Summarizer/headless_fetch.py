"""Headless browser helper for Cloudflare-protected pages."""
from __future__ import annotations

import contextlib
from typing import Optional

HEADLESS_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)


class HeadlessUnavailable(RuntimeError):
    """Raised when Playwright cannot be used for headless fetching."""


def fetch_with_playwright(url: str, *, timeout: float = 30.0) -> str:
    """Render *url* using Playwright and return the page HTML."""
    try:
        from playwright.sync_api import Browser, Playwright, TimeoutError as PlaywrightTimeoutError, sync_playwright
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise HeadlessUnavailable(
            "Playwright is not installed. Run `pip install playwright` and `playwright install`."
        ) from exc

    browser: Optional[Browser] = None
    context = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=HEADLESS_USER_AGENT,
                viewport={"width": 1280, "height": 720},
                java_script_enabled=True,
            )
            page = context.new_page()
            try:
                page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
            except PlaywrightTimeoutError as exc:
                raise HeadlessUnavailable(f"page load timed out after {timeout}s") from exc
            content = page.content()
    except HeadlessUnavailable:
        raise
    except Exception as exc:  # pragma: no cover - unexpected orchestrator failure
        raise HeadlessUnavailable(str(exc)) from exc
    finally:
        with contextlib.suppress(Exception):
            if context is not None:
                context.close()
        with contextlib.suppress(Exception):
            if browser is not None:
                browser.close()

    return content


__all__ = ["fetch_with_playwright", "HeadlessUnavailable"]
