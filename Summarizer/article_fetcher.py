"""Minimal article fetching helper with in-memory caching."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict
from urllib.parse import urlparse

import httpx

from .headless_fetch import HeadlessUnavailable, fetch_with_playwright

_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
}

_HEADLESS_MIN_TIMEOUT = 60.0
_HEADLESS_DOMAINS = {
    "dailynews.ascopubs.org",
    "www.urotoday.com",
    "ashpublications.org",
    "pmc.ncbi.nlm.nih.gov",
    "obgyn.onlinelibrary.wiley.com",
    "www.sciencedirect.com",
}

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
    timeout: float = 10.0
    max_retries: int = 2
    allow_cache: bool = True


def fetch_article(url: str, config: FetchConfig | None = None) -> str:
    """Return HTML for *url*, honoring the in-memory cache."""
    cfg = config or FetchConfig()

    if cfg.allow_cache and url in _CACHE:
        return _CACHE[url]

    headers = dict(_DEFAULT_HEADERS)
    headers.update(_env_headers_for(url))
    last_error: Exception | None = None
    attempted_headless = False

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
                not attempted_headless
                and status in {403, 429, 503}
                and _should_use_headless(url)
            ):
                attempted_headless = True
                try:
                    headless_timeout = max(cfg.timeout, _HEADLESS_MIN_TIMEOUT)
                    content = _fetch_with_playwright(url, timeout=headless_timeout)
                except HeadlessUnavailable as headless_exc:
                    last_error = FetchError(url, f"headless fallback failed: {headless_exc}")
                    break
                except Exception as headless_exc:  # pragma: no cover - unexpected
                    last_error = FetchError(url, f"headless fallback failed: {headless_exc}")
                    break
                else:
                    if cfg.allow_cache:
                        _CACHE[url] = content
                    return content
        except httpx.HTTPError as exc:
            last_error = exc

    raise FetchError(url, f"exhausted retries (last error: {last_error})", cause=last_error)


def _should_use_headless(url: str) -> bool:
    domain = urlparse(url).netloc
    return any(domain.endswith(candidate) for candidate in _HEADLESS_DOMAINS)


def _fetch_with_playwright(url: str, *, timeout: float) -> str:
    return fetch_with_playwright(url, timeout=timeout)


def _env_headers_for(url: str) -> Dict[str, str]:
    raw = os.environ.get("PRO_ALERT_HTTP_HEADERS_JSON")
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
