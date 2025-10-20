"""Minimal article fetching helper with in-memory caching."""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from time import perf_counter
from typing import Dict, Literal
from urllib.parse import urlparse

import httpx

from .config import (
    DEFAULT_HEADERS,
    HTTP_TIMEOUT,
    JINA_TIMEOUT,
    MAX_RETRIES,
    URLTOMD_TIMEOUT,
)
from .jina_fetcher import JinaConfig, JinaFetchError, fetch_with_jina
from .markdown_cleanup import clean_markdown_content
from .urltomd_fetcher import UrlToMdConfig, UrlToMdError, fetch_with_urltomd


@dataclass(slots=True)
class FetchOutcome:
    content: str
    strategy: Literal["httpx", "httpx-cache", "url-to-md", "url-to-md-cache", "jina"]
    format: Literal["html", "markdown"]
    duration: float
    removed_sections: list[str] = field(default_factory=list)


_FETCH_CONTEXT = threading.local()
_CACHE_HTML: Dict[str, str] = {}
_CACHE_MARKDOWN: Dict[str, str] = {}


class FetchError(RuntimeError):
    """Raised when the fetcher cannot return content for a URL."""

    def __init__(self, url: str, message: str, *, cause: Exception | None = None) -> None:
        super().__init__(f"Failed to fetch {url}: {message}")
        self.url = url
        self.__cause__ = cause


def clear_cache() -> None:
    """Clear both HTML and Markdown caches (mainly for tests)."""
    _CACHE_HTML.clear()
    _CACHE_MARKDOWN.clear()


def clear_markdown_cache() -> None:
    """Clear only the Markdown fallback cache."""
    _CACHE_MARKDOWN.clear()


@dataclass(frozen=True)
class FetchConfig:
    timeout: float = HTTP_TIMEOUT
    max_retries: int = MAX_RETRIES
    allow_cache: bool = True


def get_last_fetch_outcome() -> FetchOutcome | None:
    """Return metadata describing the most recent fetch on this thread."""
    return getattr(_FETCH_CONTEXT, "outcome", None)


def fetch_article(url: str, config: FetchConfig | None = None) -> str:
    """Return HTML or Markdown for *url*, honoring the in-memory caches."""
    cfg = config or FetchConfig()

    if cfg.allow_cache:
        cached_html = _CACHE_HTML.get(url)
        if cached_html is not None:
            _FETCH_CONTEXT.outcome = FetchOutcome(
                content=cached_html,
                strategy="httpx-cache",
                format="html",
                duration=0.0,
            )
            return cached_html

        cached_markdown = _CACHE_MARKDOWN.get(url)
        if cached_markdown is not None:
            _FETCH_CONTEXT.outcome = FetchOutcome(
                content=cached_markdown,
                strategy="url-to-md-cache",
                format="markdown",
                duration=0.0,
            )
            return cached_markdown

    headers = dict(DEFAULT_HEADERS)
    headers.update(_env_headers_for(url))
    last_error: Exception | None = None

    for _ in range(cfg.max_retries + 1):
        start = perf_counter()
        try:
            response = httpx.get(url, timeout=cfg.timeout, follow_redirects=True, headers=headers)
            response.raise_for_status()

            # Check for binary content that requires alternative fetch strategy
            content_type = response.headers.get('content-type', '').lower()
            binary_types = ['pdf', 'epub', 'zip', 'octet-stream']
            if any(binary_type in content_type for binary_type in binary_types):
                # Try URL transformations to find HTML versions (common patterns for academic journals)
                html_url = None

                # PDF: strip .pdf extension
                if url.lower().endswith('.pdf') or '.pdf?' in url.lower():
                    html_url = url.replace('.pdf?', '?').replace('.pdf', '')
                # EPUB: strip /epub path component
                elif url.endswith('/epub'):
                    html_url = url[:-5]  # Remove '/epub'

                if html_url:
                    try:
                        html_response = httpx.get(html_url, timeout=cfg.timeout, follow_redirects=True, headers=headers)
                        html_response.raise_for_status()
                        html_content_type = html_response.headers.get('content-type', '').lower()
                        if 'html' in html_content_type:
                            # Found HTML version, use it
                            content = html_response.text
                            elapsed = perf_counter() - start
                            if cfg.allow_cache:
                                _CACHE_HTML[url] = content  # Cache under original URL
                            _FETCH_CONTEXT.outcome = FetchOutcome(
                                content=content,
                                strategy="httpx",
                                format="html",
                                duration=elapsed,
                            )
                            return content
                    except (httpx.HTTPError, httpx.TimeoutException):
                        pass  # HTML version not available, continue to Markdown fallback

                # Trigger Markdown fallback for binary formats
                try:
                    outcome = _fetch_markdown_fallback(url, cfg.allow_cache)
                except FetchError as fallback_error:
                    last_error = fallback_error
                    break  # Exit retry loop and raise error
                else:
                    _FETCH_CONTEXT.outcome = outcome
                    return outcome.content

            content = response.text
            elapsed = perf_counter() - start
            if cfg.allow_cache:
                _CACHE_HTML[url] = content
            _FETCH_CONTEXT.outcome = FetchOutcome(
                content=content,
                strategy="httpx",
                format="html",
                duration=elapsed,
            )
            return content
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            body = exc.response.text[:200].replace("\n", " ")
            last_error = FetchError(url, f"HTTP {status}: {body}")

            if status in {403, 429, 503}:
                try:
                    outcome = _fetch_markdown_fallback(url, cfg.allow_cache)
                except FetchError as fallback_error:
                    last_error = fallback_error
                else:
                    _FETCH_CONTEXT.outcome = outcome
                    return outcome.content
        except httpx.HTTPError as exc:
            last_error = exc

    raise FetchError(url, f"exhausted retries (last error: {last_error})", cause=last_error)


def _fetch_markdown_fallback(url: str, allow_cache: bool) -> FetchOutcome:
    """Fetch Markdown using url-to-md or Jina and return outcome metadata."""
    if allow_cache and url in _CACHE_MARKDOWN:
        cleaned = _CACHE_MARKDOWN[url]
        return FetchOutcome(
            content=cleaned,
            strategy="url-to-md-cache",
            format="markdown",
            duration=0.0,
        )

    start = perf_counter()
    try:
        markdown = fetch_with_urltomd(url, UrlToMdConfig(timeout=URLTOMD_TIMEOUT))
        strategy: Literal["url-to-md", "jina"] = "url-to-md"
    except UrlToMdError as exc:
        try:
            markdown = fetch_with_jina(url, JinaConfig(timeout=JINA_TIMEOUT))
            strategy = "jina"
        except JinaFetchError as jina_exc:
            raise FetchError(
                url,
                f"fallback failed (url-to-md: {exc}; jina: {jina_exc})",
                cause=jina_exc,
            ) from jina_exc

    cleaned, removed = clean_markdown_content(markdown)
    elapsed = perf_counter() - start

    if allow_cache:
        _CACHE_MARKDOWN[url] = cleaned

    return FetchOutcome(
        content=cleaned,
        strategy=strategy,
        format="markdown",
        duration=elapsed,
        removed_sections=list(removed),
    )


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
    "FetchOutcome",
    "clear_cache",
    "clear_markdown_cache",
    "fetch_article",
    "get_last_fetch_outcome",
]
