"""url-to-md CLI wrapper used for Markdown fallbacks."""
from __future__ import annotations

import os
import signal
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

    proc = None
    try:
        # Use Popen with process group for clean subprocess tree termination
        # start_new_session=True creates new process group, allowing us to kill
        # Chrome children spawned by Puppeteer when url-to-md times out
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )

        stdout, stderr = proc.communicate(timeout=cfg.timeout + 5)

    except subprocess.TimeoutExpired:
        # Kill entire process group (Chrome children included)
        if proc is not None:
            try:
                pgid = os.getpgid(proc.pid)
                os.killpg(pgid, signal.SIGTERM)
                proc.wait(timeout=2)
            except (ProcessLookupError, OSError):
                pass
            except subprocess.TimeoutExpired:
                # Force kill if SIGTERM didn't work
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    pass
            finally:
                try:
                    proc.kill()
                    proc.wait(timeout=1)
                except Exception:
                    pass
        raise UrlToMdError(url, f"timeout after {cfg.timeout}s")
    except FileNotFoundError as exc:
        raise UrlToMdError(url, "url-to-md binary not found") from exc
    except Exception as exc:
        # Clean up process on any error
        if proc is not None:
            try:
                proc.kill()
                proc.wait(timeout=1)
            except Exception:
                pass
        raise UrlToMdError(url, str(exc)) from exc

    if proc.returncode != 0:
        message = stderr.strip() or f"exit code {proc.returncode}"
        raise UrlToMdError(url, message)

    markdown = stdout.strip()
    if not markdown:
        raise UrlToMdError(url, "no content returned")

    return markdown


__all__ = [
    "UrlToMdConfig",
    "UrlToMdError",
    "fetch_with_urltomd",
]
