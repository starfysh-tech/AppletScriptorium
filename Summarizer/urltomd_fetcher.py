"""url-to-md CLI wrapper used for Markdown fallbacks."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Sequence


class UrlToMdError(RuntimeError):
    """Raised when url-to-md cannot return content for a URL."""

    def __init__(self, url: str, message: str) -> None:
        super().__init__(f"url-to-md failed for {url}: {message}")
        self.url = url


@dataclass(frozen=True)
class UrlToMdConfig:
    """Configuration passed to url-to-md CLI."""

    timeout: float = 10.0
    include_tags: Sequence[str] = ("p", "h2", "h3", "h4", "img")
    remove_tags: Sequence[str] = ("nav", "header", "footer", "aside", "script")
    clean_content: bool = True


def fetch_with_urltomd(url: str, config: UrlToMdConfig | None = None) -> str:
    """Fetch URL using url-to-md CLI and return Markdown."""
    cfg = config or UrlToMdConfig()

    cmd = ["url-to-md", url, "--wait", str(cfg.timeout)]

    if cfg.include_tags:
        cmd.append("--include-tags")
        cmd.extend(cfg.include_tags)
    if cfg.remove_tags:
        cmd.append("--remove-tags")
        cmd.extend(cfg.remove_tags)
    if cfg.clean_content:
        cmd.append("--clean-content")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=cfg.timeout + 5,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise UrlToMdError(url, f"timeout after {cfg.timeout}s") from exc
    except FileNotFoundError as exc:
        raise UrlToMdError(url, "url-to-md binary not found") from exc
    except Exception as exc:
        raise UrlToMdError(url, str(exc)) from exc

    if result.returncode != 0:
        message = result.stderr.strip() or f"exit code {result.returncode}"
        raise UrlToMdError(url, message)

    markdown = result.stdout.strip()
    if not markdown:
        raise UrlToMdError(url, "no content returned")

    return markdown


__all__ = [
    "UrlToMdConfig",
    "UrlToMdError",
    "fetch_with_urltomd",
]
