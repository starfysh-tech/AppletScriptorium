"""Jina AI Reader API wrapper used as final Markdown fallback."""
from __future__ import annotations

import os
from dataclasses import dataclass

import httpx


class JinaFetchError(RuntimeError):
    """Raised when the Jina Reader API fails."""

    def __init__(self, url: str, message: str) -> None:
        super().__init__(f"Jina AI failed for {url}: {message}")
        self.url = url


@dataclass(frozen=True)
class JinaConfig:
    timeout: float = 30.0
    api_key: str | None = None


def fetch_with_jina(url: str, config: JinaConfig | None = None) -> str:
    """Fetch URL using Jina Reader API and return Markdown."""
    cfg = config or JinaConfig()
    api_key = cfg.api_key or os.environ.get("JINA_API_KEY")
    if not api_key:
        raise JinaFetchError(url, "JINA_API_KEY not configured")

    jina_url = f"https://r.jina.ai/{url}"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = httpx.get(jina_url, headers=headers, timeout=cfg.timeout)
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise JinaFetchError(url, f"timeout after {cfg.timeout}s") from exc
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:200]
        raise JinaFetchError(url, f"HTTP {exc.response.status_code}: {body}") from exc
    except Exception as exc:
        raise JinaFetchError(url, str(exc)) from exc

    markdown = response.text.strip()
    if not markdown:
        raise JinaFetchError(url, "empty response")

    return markdown


__all__ = [
    "JinaConfig",
    "JinaFetchError",
    "fetch_with_jina",
]
