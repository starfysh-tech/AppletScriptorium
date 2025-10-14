"""Minimal article fetching helper with in-memory caching."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict
from urllib.parse import urlparse

import httpx

from .config import (
    CRAWLEE_DOMAINS,
    CRAWLEE_MIN_TIMEOUT,
    DEFAULT_HEADERS,
    HEADED_DOMAINS,
    HTTP_TIMEOUT,
    MAX_RETRIES,
)
from .crawlee_fetcher import CrawleeFetchConfig, CrawleeFetchError, fetch_with_crawlee_sync

_CACHE: Dict[str, str] = {}


class FetchError(RuntimeError):
    """Raised when the fetcher cannot return content for a URL."""

    def __init__(self, url: str, message: str, *, cause: Exception | None = None) -> None:
        super().__init__(f"Failed to fetch {url}: {message}")
        self.url = url
        self.__cause__ = cause


def clear_cache() -> None:
    """Clear the in-memory cache (mainly for tests)."""
    _CACHE.clear()


@dataclass(frozen=True)
class FetchConfig:
    timeout: float = HTTP_TIMEOUT
    max_retries: int = MAX_RETRIES
    allow_cache: bool = True


def fetch_article(url: str, config: FetchConfig | None = None) -> str:
    """Return HTML for *url*, honoring the in-memory cache."""
    cfg = config or FetchConfig()

    if cfg.allow_cache and url in _CACHE:
        return _CACHE[url]

    headers = dict(DEFAULT_HEADERS)
    headers.update(_env_headers_for(url))
    last_error: Exception | None = None
    attempted_crawlee = False

    for _ in range(cfg.max_retries + 1):
        try:
            response = httpx.get(url, timeout=cfg.timeout, follow_redirects=True, headers=headers)
            response.raise_for_status()
            content = response.text
            if cfg.allow_cache:
                _CACHE[url] = content
            return content
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            body = exc.response.text[:200].replace("\n", " ")
            last_error = FetchError(url, f"HTTP {status}: {body}")

            if (
                not attempted_crawlee
                and status in {403, 429, 503}
                and _should_use_crawlee(url)
            ):
                attempted_crawlee = True
                try:
                    crawlee_timeout = max(cfg.timeout, CRAWLEE_MIN_TIMEOUT)
                    # Use headed mode for domains with aggressive bot detection
                    headless = not _requires_headed_mode(url)
                    content = fetch_with_crawlee_sync(
                        url,
                        CrawleeFetchConfig(timeout=crawlee_timeout, headless=headless, browser_type="chromium"),
                    )
                except CrawleeFetchError as crawlee_exc:
                    last_error = FetchError(url, f"crawlee fallback failed: {crawlee_exc}")
                    break
                else:
                    if cfg.allow_cache:
                        _CACHE[url] = content
                    return content
        except httpx.HTTPError as exc:
            last_error = exc

    raise FetchError(url, f"exhausted retries (last error: {last_error})", cause=last_error)


def _should_use_crawlee(url: str) -> bool:
    domain = urlparse(url).netloc
    return any(domain.endswith(candidate) for candidate in CRAWLEE_DOMAINS)


def _requires_headed_mode(url: str) -> bool:
    """Check if URL requires headed (non-headless) browser mode."""
    domain = urlparse(url).netloc
    return any(domain.endswith(candidate) for candidate in HEADED_DOMAINS)


def _env_headers_for(url: str) -> Dict[str, str]:
    raw = os.environ.get("ALERT_HTTP_HEADERS_JSON")
    if not raw:
        return {}
    try:
        mapping = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    if not isinstance(mapping, dict):
        return {}

    domain = urlparse(url).netloc
    headers: Dict[str, str] = {}
    for key, value in mapping.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        if key in domain:
            for header_name, header_value in value.items():
                if isinstance(header_name, str) and isinstance(header_value, str):
                    headers[header_name] = header_value
    return headers


__all__ = [
    "FetchConfig",
    "FetchError",
    "clear_cache",
    "fetch_article",
]
