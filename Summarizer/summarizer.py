"""Interface for generating article summaries via Ollama."""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, List

from .config import DEFAULT_MODEL, TEMPERATURE, MAX_TOKENS, OLLAMA_TIMEOUT, SUMMARY_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class SummarizerError(RuntimeError):
    """Raised when summary generation fails."""


@dataclass(frozen=True)
class SummarizerConfig:
    model: str = DEFAULT_MODEL
    temperature: float = TEMPERATURE
    max_tokens: int = MAX_TOKENS


ArticleDict = dict[str, Any]
RunnerType = Callable[[str, SummarizerConfig], str]


def summarize_article(article: ArticleDict, *, config: SummarizerConfig | None = None, runner: RunnerType | None = None) -> dict[str, Any]:
    """Summarize an article using the configured backend."""
    cfg = config or SummarizerConfig()
    backend = runner or _run_with_ollama
    prompt = _build_prompt(article)

    try:
        raw_output = backend(prompt, cfg)
    except SummarizerError:
        raise
    except Exception as exc:  # pragma: no cover - treated uniformly
        raise SummarizerError(f"Failed to summarize {article.get('url', 'article')}") from exc

    bullets = _parse_bullets(raw_output)
    if not bullets:
        raise SummarizerError("No summary bullets returned by backend")

    return {
        "title": article.get("title", ""),
        "url": article.get("url"),
        "summary": [{"type": "bullet", "text": bullet} for bullet in bullets],
        "model": cfg.model,
    }


def _build_prompt(article: ArticleDict) -> str:
    content = article.get("content", "")
    if isinstance(content, list):  # backward compatibility
        fragments: List[str] = []
        for block in content:
            text = block.get("text") or ""
            if text:
                fragments.append(text)
            items = block.get("items") if isinstance(block, dict) else None
            if items:
                fragments.extend(str(item) for item in items if item)
        content_text = "\n".join(fragments)
    else:
        content_text = str(content)

    title = article.get("title", "")
    return f"Title: {title}\n\nArticle content:\n{content_text}\n\n{SUMMARY_PROMPT_TEMPLATE}"


def _attempt_ollama_restart() -> bool:
    """Try to recover unresponsive Ollama daemon.

    Attempts: kill process (will auto-restart via launchd) → brew services restart.
    """
    try:
        # Kill unresponsive process; launchd auto-relaunches it
        kill_result = subprocess.run(
            ["pkill", "-f", "ollama serve"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5.0,
        )
        if kill_result.returncode in (0, 1):  # 0=killed, 1=no process found
            logger.info("Killed unresponsive ollama serve process; launchd will restart")
            return True
    except Exception as exc:
        logger.debug("Could not kill ollama process: %s", exc)

    # Fallback: brew services restart (works if installed via Homebrew)
    try:
        brew_result = subprocess.run(
            ["brew", "services", "restart", "ollama"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10.0,
        )
        if brew_result.returncode == 0:
            logger.info("Restarted Ollama via brew services")
            return True
    except Exception as exc:
        logger.debug("Could not restart ollama via brew: %s", exc)

    return False


def _run_with_ollama(prompt: str, cfg: SummarizerConfig) -> str:
    """Call Ollama with timeout and auto-restart on hang.

    Detects when Ollama daemon is unresponsive, attempts restart, and retries once.
    """
    args = [
        "ollama",
        "run",
        cfg.model,
    ]

    for attempt in range(2):
        try:
            process = subprocess.run(
                args,
                input=prompt,
                capture_output=True,
                text=True,
                check=False,
                timeout=OLLAMA_TIMEOUT,
            )
            if process.returncode != 0:
                raise SummarizerError(process.stderr.strip() or "unknown ollama error")
            return process.stdout.strip()
        except subprocess.TimeoutExpired:
            if attempt == 0:
                logger.error("Ollama unresponsive (timeout after %.0fs); attempting restart", OLLAMA_TIMEOUT)
                _attempt_ollama_restart()
                logger.info("Retrying summarization after restart attempt")
            else:
                # Second attempt failed
                raise SummarizerError(
                    f"Ollama unresponsive (timed out after {OLLAMA_TIMEOUT}s); restart failed or still unresponsive"
                )


def _parse_bullets(output: str) -> List[str]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    bullets: List[str] = []
    for line in lines:
        if line.startswith("- ") or line.startswith("* "):
            bullets.append(line[2:].strip())
        elif line and line[0].isdigit() and line[1:3] in {". ", ") "}:
            bullets.append(line[3:].strip())
    if not bullets and output:
        bullets = _sentence_split(output)
    return [bullet for bullet in bullets if bullet]


def _sentence_split(text: str) -> List[str]:
    sentences = []
    buffer = ""
    for char in text:
        buffer += char
        if char in ".!?":
            cleaned = buffer.strip()
            if cleaned:
                sentences.append(cleaned)
            buffer = ""
    if buffer.strip():
        sentences.append(buffer.strip())
    return sentences[:3]


__all__ = ["summarize_article", "SummarizerConfig", "SummarizerError"]
