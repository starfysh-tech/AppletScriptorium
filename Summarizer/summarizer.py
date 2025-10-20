"""Interface for generating article summaries via LM Studio with optional Ollama fallback.

Backend selection:
- Primary: LM Studio (if LMSTUDIO_BASE_URL is set in .env)
- Fallback: Ollama (if OLLAMA_ENABLED=true in .env)
  - WARNING: Ollama may significantly slow down your computer during processing
  - Only used when LM Studio fails

Configure all backends in .env file - see config.py for available settings.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, List, Optional

import httpx

from .config import (
    DEFAULT_MODEL,
    TEMPERATURE,
    MAX_TOKENS,
    OLLAMA_ENABLED,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    LMSTUDIO_BASE_URL,
    LMSTUDIO_MODEL,
    LMSTUDIO_TIMEOUT,
    LMSTUDIO_HEALTH_TIMEOUT,
    SUMMARY_PROMPT_TEMPLATE,
)

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
    """Summarize an article using configured LLM backend.

    Backend selection:
    - If runner is provided: Use custom runner (for testing)
    - If LMSTUDIO_BASE_URL is set: Use LM Studio as primary
      - If LM Studio fails AND OLLAMA_ENABLED=true: Fall back to Ollama
      - If LM Studio fails AND OLLAMA_ENABLED=false: Raise error
    - If LMSTUDIO_BASE_URL not set: Raise error (must configure at least one backend)

    Raises SummarizerError on any failure.
    """
    cfg = config or SummarizerConfig()
    prompt = _build_prompt(article)
    url = article.get('url', 'unknown')

    # Custom runner for testing
    if runner:
        logger.debug("[custom] Using provided runner for %s", url)
        try:
            raw_output = runner(prompt, cfg)
            model_name = cfg.model
            backend_used = "custom"
        except SummarizerError:
            raise
        except Exception as exc:  # pragma: no cover
            raise SummarizerError(f"Custom runner failed for {url}") from exc
    # LM Studio backend with optional Ollama fallback
    elif LMSTUDIO_BASE_URL:
        if not LMSTUDIO_MODEL:
            raise SummarizerError("LMSTUDIO_BASE_URL set but LMSTUDIO_MODEL not configured in .env")

        logger.info("[lmstudio] Calling %s at %s for %s", LMSTUDIO_MODEL, LMSTUDIO_BASE_URL, url)
        try:
            raw_output = _run_with_lmstudio(prompt, cfg)
            model_name = LMSTUDIO_MODEL
            backend_used = "lmstudio"
        except SummarizerError as exc:
            logger.error("[lmstudio] Failed for %s: %s", url, exc)

            # Try Ollama fallback if enabled
            if OLLAMA_ENABLED:
                logger.warning("[lmstudio] Falling back to Ollama (WARNING: may slow down computer)")
                try:
                    raw_output = _run_with_ollama(prompt, cfg)
                    model_name = OLLAMA_MODEL
                    backend_used = "ollama"
                except SummarizerError as ollama_exc:
                    logger.error("[ollama] Fallback also failed: %s", ollama_exc)
                    raise SummarizerError(f"Both LM Studio and Ollama failed for {url}") from ollama_exc
            else:
                # No fallback configured
                raise
    # No backend configured
    else:
        raise SummarizerError(
            "No LLM backend configured. Set LMSTUDIO_BASE_URL and LMSTUDIO_MODEL in .env file"
        )

    bullets = _parse_bullets(raw_output)
    if not bullets:
        logger.error("[%s] No bullets parsed from response for %s", backend_used, url)
        raise SummarizerError(f"No summary bullets returned by {backend_used}")

    logger.info("[%s] Successfully summarized %s", backend_used, url)

    return {
        "title": article.get("title", ""),
        "url": url,
        "summary": [{"type": "bullet", "text": bullet} for bullet in bullets],
        "model": model_name,
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


def _test_lmstudio_availability(base_url: str) -> bool:
    """Fast health check to verify LM Studio is responsive.

    Returns True if LM Studio responds to /v1/models within timeout.
    """
    try:
        with httpx.Client(timeout=LMSTUDIO_HEALTH_TIMEOUT) as client:
            response = client.get(f"{base_url}/v1/models")
            if response.status_code == 200:
                logger.debug("[lmstudio] Health check passed at %s", base_url)
                return True
            logger.warning("[lmstudio] Health check returned status %d", response.status_code)
            return False
    except httpx.TimeoutException:
        logger.warning("[lmstudio] Health check timed out after %.1fs", LMSTUDIO_HEALTH_TIMEOUT)
        return False
    except httpx.ConnectError as exc:
        logger.warning("[lmstudio] Connection failed: %s", exc)
        return False
    except (httpx.RequestError, httpx.InvalidURL) as exc:
        logger.warning("[lmstudio] Health check error: %s", exc)
        return False


def _run_with_lmstudio(prompt: str, cfg: SummarizerConfig) -> str:
    """Call LM Studio API using OpenAI-compatible endpoint.

    Raises SummarizerError on any failure with informative error messages.
    """
    if not LMSTUDIO_BASE_URL:
        raise SummarizerError("LMSTUDIO_BASE_URL not configured in .env")

    # Fast health check before attempting request
    logger.debug("[lmstudio] Running health check")
    if not _test_lmstudio_availability(LMSTUDIO_BASE_URL):
        raise SummarizerError(
            f"LM Studio not available at {LMSTUDIO_BASE_URL} "
            f"(check server is running and network is accessible)"
        )

    url = f"{LMSTUDIO_BASE_URL}/v1/chat/completions"
    payload = {
        "model": LMSTUDIO_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_TOKENS,
        "temperature": cfg.temperature,
    }

    # Log prompt size for debugging oversized payloads
    prompt_chars = len(prompt)
    estimated_tokens = prompt_chars // 4
    logger.debug(
        "[lmstudio] Sending request to %s (timeout: %.1fs, prompt: %d chars / ~%d tokens)",
        url, LMSTUDIO_TIMEOUT, prompt_chars, estimated_tokens
    )

    try:
        with httpx.Client(timeout=LMSTUDIO_TIMEOUT) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract content from OpenAI-compatible response
            if "choices" not in data or not data["choices"]:
                logger.error("[lmstudio] Invalid response structure: %s", data)
                raise SummarizerError("LM Studio returned empty response")

            content = data["choices"][0]["message"]["content"]
            logger.debug("[lmstudio] Received %d chars from model", len(content))
            return content.strip()

    except httpx.TimeoutException:
        raise SummarizerError(
            f"LM Studio timed out after {LMSTUDIO_TIMEOUT}s "
            f"(consider increasing LMSTUDIO_TIMEOUT in .env or using faster model)"
        )
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        body = exc.response.text[:200].replace("\n", " ")
        logger.error("[lmstudio] HTTP %d response: %s", status, body)
        raise SummarizerError(f"LM Studio HTTP {status}: {body}")
    except httpx.InvalidURL as exc:
        raise SummarizerError(f"Invalid LMSTUDIO_BASE_URL in .env: {exc}")
    except httpx.RequestError as exc:
        raise SummarizerError(f"LM Studio connection error: {exc}")
    except (KeyError, json.JSONDecodeError) as exc:
        logger.error("[lmstudio] Response parsing error: %s", exc)
        raise SummarizerError(f"LM Studio returned invalid JSON response")


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


def _normalize_bullet_tags(bullet: str) -> str:
    """Normalize tag formatting in bullets to ensure consistency.

    Adds emojis to tags if missing and normalizes case.
    """
    # Tactical Win tag normalization
    tactical_mappings = {
        "SHIP NOW": "🚀 SHIP NOW",
        "ROADMAP": "🗺️ ROADMAP",
        "WATCH": "👀 WATCH",
    }

    # Market Signal tag normalization
    market_mappings = {
        "URGENT": "🔴 URGENT",
        "NOTABLE": "🟡 NOTABLE",
        "CONTEXT": "⚫ CONTEXT",
    }

    # Process bullet text
    result = bullet

    # Normalize tactical tags (case-insensitive)
    for base_tag, full_tag in tactical_mappings.items():
        # Match [TAG] or [emoji TAG] variations, case-insensitive
        pattern = r'\[(?:[^\]]*\s+)?' + re.escape(base_tag) + r'\]'
        if re.search(pattern, result, re.IGNORECASE):
            # Replace with normalized version
            result = re.sub(pattern, f'[{full_tag}]', result, flags=re.IGNORECASE)

    # Normalize market signal tags (case-insensitive)
    for base_tag, full_tag in market_mappings.items():
        pattern = r'\[(?:[^\]]*\s+)?' + re.escape(base_tag) + r'\]'
        if re.search(pattern, result, re.IGNORECASE):
            result = re.sub(pattern, f'[{full_tag}]', result, flags=re.IGNORECASE)

    return result


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

    # Normalize tags in all bullets
    bullets = [_normalize_bullet_tags(bullet) for bullet in bullets if bullet]
    return bullets


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
