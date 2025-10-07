"""Minimal article fetching helper with in-memory caching and stub support."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import httpx

_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
}

_CACHE: Dict[str, str] = {}
_MANIFEST_CACHE: Dict[Path, Dict[str, str]] = {}


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
    stub_manifest: Optional[Path] = None
    allow_cache: bool = True


def fetch_article(url: str, config: FetchConfig | None = None) -> str:
    """Return HTML for *url*, honoring in-memory cache and stub manifest."""
    cfg = config or FetchConfig()

    if cfg.allow_cache and url in _CACHE:
        return _CACHE[url]

    stub_content = _maybe_load_from_stub(url, cfg.stub_manifest)
    if stub_content is not None:
        if cfg.allow_cache:
            _CACHE[url] = stub_content
        return stub_content

    headers = dict(_DEFAULT_HEADERS)
    last_error: Exception | None = None

    for attempt in range(cfg.max_retries + 1):
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
        except httpx.HTTPError as exc:
            last_error = exc

    raise FetchError(url, f"exhausted retries (last error: {last_error})", cause=last_error)


def _maybe_load_from_stub(url: str, manifest_path: Optional[Path]) -> Optional[str]:
    if manifest_path is None:
        return None

    manifest_path = manifest_path.resolve()
    manifest = _MANIFEST_CACHE.get(manifest_path)
    if manifest is None:
        if not manifest_path.exists():
            raise FetchError(url, f"stub manifest {manifest_path} not found")
        try:
            mapping = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise FetchError(url, f"stub manifest {manifest_path} is not valid JSON") from exc
        if not isinstance(mapping, dict):
            raise FetchError(url, f"stub manifest {manifest_path} must map URLs to paths")
        manifest = {str(k): str(v) for k, v in mapping.items()}
        _MANIFEST_CACHE[manifest_path] = manifest

    target = manifest.get(url)
    if not target:
        return None

    target_path = Path(target)
    if not target_path.is_absolute():
        target_path = manifest_path.parent / target_path

    if not target_path.exists():
        raise FetchError(url, f"stub file {target_path} not found")

    return target_path.read_text(encoding="utf-8")


__all__ = [
    "FetchConfig",
    "FetchError",
    "clear_cache",
    "fetch_article",
]
