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
from pathlib import Path
from typing import Any, Callable, List, Literal, Optional

import httpx

from .config import (
    ARTICLE_TYPE_PROMPT,
    ARTICLE_TYPES,
    DEFAULT_MODEL,
    TEMPERATURE,
    MAX_TOKENS,
    MAX_CONTENT_CHARS,
    OLLAMA_BASE_URL,
    OLLAMA_ENABLED,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    LMSTUDIO_BASE_URL,
    LMSTUDIO_MODEL,
    LMSTUDIO_TIMEOUT,
    LMSTUDIO_HEALTH_TIMEOUT,
    SUMMARY_PROMPT_TEMPLATE,
    SUMMARY_PROMPTS,
    SUMMARY_JSON_SCHEMA,
)

logger = logging.getLogger(__name__)

# Full path to LM Studio CLI (not in PATH when run from Mail.app)
LMS_CLI = Path.home() / ".lmstudio" / "bin" / "lms"


class SummarizerError(RuntimeError):
    """Raised when summary generation fails."""


@dataclass(frozen=True)
class SummarizerConfig:
    model: str = DEFAULT_MODEL
    temperature: float = TEMPERATURE
    max_tokens: int = MAX_TOKENS


ArticleDict = dict[str, Any]
RunnerType = Callable[[str, SummarizerConfig], str]


def summarize_article(
    article: ArticleDict,
    *,
    config: SummarizerConfig | None = None,
    runner: RunnerType | None = None,
    backend: Literal["lmstudio", "ollama"] | None = None,
) -> dict[str, Any]:
    """Summarize an article using configured LLM backend with retry on validation failure.

    Args:
        article: Article dictionary with title, url, content
        config: Optional SummarizerConfig (defaults to SummarizerConfig())
        runner: Optional custom runner for testing (bypasses backend selection)
        backend: Optional backend override ("lmstudio" or "ollama")
            - If specified: Use only this backend (no auto-fallback)
            - If None: Use auto-fallback behavior (LM Studio → Ollama if enabled)

    Backend selection:
    - If runner is provided: Use custom runner (for testing)
    - If backend is specified: Use only that backend (no fallback)
    - If backend is None and LMSTUDIO_BASE_URL is set: Use LM Studio as primary
      - If LM Studio fails AND OLLAMA_ENABLED=true: Fall back to Ollama
      - If LM Studio fails AND OLLAMA_ENABLED=false: Raise error
    - If backend is None and LMSTUDIO_BASE_URL not set: Raise error

    Validation and retry:
    - After parsing bullets, validates required structure (4 bullets with required labels)
    - On validation failure: Retries once (2 total attempts)
    - After all retries: Raises SummarizerError with validation details

    Raises SummarizerError on any failure.
    """
    # TODO: Refactor to use separate LLM calls with dedicated prompts for each bullet type
    # (KEY FINDING, TACTICAL WIN, MARKET SIGNAL, CONCERN) instead of single monolithic prompt.
    # This would allow better control over each bullet's focus and reduce format confusion.

    cfg = config or SummarizerConfig()
    url = article.get('url', 'unknown')

    # Classify article type to select appropriate prompt
    article_type = classify_article_type(article, config=cfg)
    logger.info("[classify] Article type for %s: %s", url, article_type)

    prompt = _build_prompt(article, article_type=article_type)

    # Retry loop for validation failures
    max_attempts = 2
    last_validation_error = ""

    for attempt in range(1, max_attempts + 1):
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
        # Explicit backend specified (no auto-fallback)
        elif backend == "lmstudio":
            if not LMSTUDIO_BASE_URL or not LMSTUDIO_MODEL:
                raise SummarizerError("LM Studio backend requested but LMSTUDIO_BASE_URL or LMSTUDIO_MODEL not configured in .env")

            logger.info("[lmstudio] Calling %s at %s for %s (attempt %d/%d)", LMSTUDIO_MODEL, LMSTUDIO_BASE_URL, url, attempt, max_attempts)
            try:
                raw_output = _run_with_lmstudio(prompt, cfg)
                model_name = cfg.model or LMSTUDIO_MODEL
                backend_used = "lmstudio"
            except SummarizerError:
                raise  # No fallback when backend is explicitly specified
        elif backend == "ollama":
            logger.info("[ollama] Calling %s for %s (attempt %d/%d)", cfg.model or OLLAMA_MODEL, url, attempt, max_attempts)
            try:
                raw_output = _run_with_ollama(prompt, cfg)
                model_name = cfg.model or OLLAMA_MODEL
                backend_used = "ollama"
            except SummarizerError:
                raise  # No fallback when backend is explicitly specified
        # Auto-fallback mode: LM Studio with optional Ollama fallback
        elif LMSTUDIO_BASE_URL:
            if not LMSTUDIO_MODEL:
                raise SummarizerError("LMSTUDIO_BASE_URL set but LMSTUDIO_MODEL not configured in .env")

            logger.info("[lmstudio] Calling %s at %s for %s (attempt %d/%d)", LMSTUDIO_MODEL, LMSTUDIO_BASE_URL, url, attempt, max_attempts)
            try:
                raw_output = _run_with_lmstudio(prompt, cfg)
                model_name = cfg.model or LMSTUDIO_MODEL
                backend_used = "lmstudio"
            except SummarizerError as exc:
                logger.error("[lmstudio] Failed for %s: %s", url, exc)

                # Try Ollama fallback if enabled
                if OLLAMA_ENABLED:
                    logger.warning("[lmstudio] Falling back to Ollama (WARNING: may slow down computer)")
                    try:
                        raw_output = _run_with_ollama(prompt, cfg)
                        model_name = cfg.model or OLLAMA_MODEL
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

        # Log raw LLM output for diagnosis
        logger.debug("[%s][debug] Raw LLM output (%d chars): %s", backend_used, len(raw_output), raw_output[:500])
        if len(raw_output) > 500:
            logger.debug("[%s][debug] Raw LLM output (remaining): %s", backend_used, raw_output[500:])

        # Parse and validate bullets
        bullets = _parse_bullets(raw_output)

        # Log parsed bullet details
        logger.debug("[%s][debug] Parsed %d bullets from output", backend_used, len(bullets))
        for i, bullet in enumerate(bullets, 1):
            logger.debug("[%s][debug] Bullet %d: %s", backend_used, i, bullet[:100])

        if not bullets:
            logger.error("[%s] No bullets parsed from response for %s", backend_used, url)
            raise SummarizerError(f"No summary bullets returned by {backend_used}")

        # Parse actionability indicator
        actionability = _parse_actionability(raw_output)
        if actionability:
            logger.debug("[%s][debug] Parsed actionability: %s", backend_used, actionability)

        # Validate bullet structure
        is_valid, validation_error = _validate_bullet_structure(bullets, raw_output)
        if is_valid:
            logger.info("[%s] Successfully summarized %s", backend_used, url)
            result = {
                "title": article.get("title", ""),
                "url": url,
                "publisher": article.get("publisher", ""),
                "snippet": article.get("snippet", ""),
                "summary": [{"type": "bullet", "text": bullet} for bullet in bullets],
                "model": model_name,
            }
            if actionability:
                result["actionability"] = actionability
            return result

        # Validation failed
        last_validation_error = validation_error
        if attempt < max_attempts:
            logger.warning("[validate] %s for %s - retrying (attempt %d/%d)", validation_error, url, attempt + 1, max_attempts)
        else:
            logger.error("[validate] %s for %s - all retries exhausted", validation_error, url)

    # All retries exhausted
    raise SummarizerError(f"Summary validation failed after {max_attempts} attempts: {last_validation_error}")


def classify_article_type(article: ArticleDict, *, config: SummarizerConfig | None = None) -> str:
    """Classify article type using LM Studio to select appropriate summarization prompt.

    Args:
        article: Article dictionary with content
        config: Optional SummarizerConfig

    Returns:
        One of: "RESEARCH", "NEWS", "OPINION", "PRESS_RELEASE"
        Falls back to "NEWS" if classification fails or LM Studio unavailable
    """
    cfg = config or SummarizerConfig()

    # Extract first ~500 words to save tokens
    content = article.get("content", "")
    if isinstance(content, list):
        # Handle legacy format
        fragments: List[str] = []
        for block in content:
            text = block.get("text") or ""
            if text:
                fragments.append(text)
        content_text = "\n".join(fragments)
    else:
        content_text = str(content)

    # Truncate to ~500 words (rough: 4 chars per word)
    truncated = content_text[:2000]

    prompt = ARTICLE_TYPE_PROMPT.format(content=truncated)

    try:
        # Use LM Studio for classification
        raw_output = _run_with_lmstudio(prompt, cfg)
        detected_type = raw_output.strip().upper()

        # Validate response
        if detected_type in ARTICLE_TYPES:
            logger.info("[classify] Detected article type: %s", detected_type)
            return detected_type
        else:
            logger.warning("[classify] Invalid type '%s', falling back to NEWS", detected_type)
            return "NEWS"

    except Exception as exc:
        logger.warning("[classify] Classification failed: %s - falling back to NEWS", exc)
        return "NEWS"


def _truncate_content(content: str, max_chars: int) -> str:
    """Truncate content to fit within context window, preserving sentence boundaries.

    Args:
        content: Article content text
        max_chars: Maximum characters allowed

    Returns:
        Original content if under limit, otherwise truncated at sentence boundary
        with "[Content truncated...]" marker appended.

    Tries to end at sentence boundary (". ") while keeping at least 80% of max_chars.
    """
    if len(content) <= max_chars:
        return content

    # Try to find sentence boundary in last 20% of allowed content
    min_length = int(max_chars * 0.8)
    truncated = content[:max_chars]

    # Search for last sentence boundary between min_length and max_chars
    last_period = truncated.rfind(". ", min_length)

    if last_period > 0:
        # Found a sentence boundary in the acceptable range
        result = truncated[:last_period + 1]  # Include the period
    else:
        # No sentence boundary found, use hard cutoff
        result = truncated

    return result + "\n\n[Content truncated to fit context window]"


def _build_prompt(article: ArticleDict, article_type: str | None = None) -> str:
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

    # Truncate content to fit context window
    content_text = _truncate_content(content_text, MAX_CONTENT_CHARS)

    title = article.get("title", "")

    # Select prompt based on article type
    if article_type and article_type in SUMMARY_PROMPTS:
        prompt_template = SUMMARY_PROMPTS[article_type]
    else:
        prompt_template = SUMMARY_PROMPT_TEMPLATE

    return f"Title: {title}\n\nArticle content:\n{content_text}\n\n{prompt_template}"


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


def _get_loaded_models(base_url: str) -> list[str]:
    """Get list of currently loaded model IDs from LM Studio.

    Returns empty list if cannot connect or no models loaded.
    """
    try:
        with httpx.Client(timeout=LMSTUDIO_HEALTH_TIMEOUT) as client:
            response = client.get(f"{base_url}/v1/models")
            if response.status_code == 200:
                data = response.json()
                return [model["id"] for model in data.get("data", [])]
    except Exception:
        pass
    return []


def _ensure_correct_model_loaded(base_url: str, target_model: str) -> tuple[bool, str]:
    """Ensure ONLY the target model is loaded in LM Studio.

    If other models are loaded or target is not loaded, unloads all models
    and loads only the target model.

    Args:
        base_url: LM Studio API base URL
        target_model: Model identifier to load (from LMSTUDIO_MODEL)

    Returns:
        (success: bool, message: str)
    """
    import time

    loaded = _get_loaded_models(base_url)

    # Model already available - no action needed
    if target_model in loaded:
        logger.info("[lmstudio] Model already available: %s", target_model)
        return True, f"Using {target_model}"

    # Model not available - load it (no need to unload others)
    logger.info("[lmstudio] Model %s not in available list, loading...", target_model)

    # Skip unload - LM Studio can have multiple models available
    if False:  # Disabled: was causing issues with multi-model LM Studio setups
        try:
            result = subprocess.run(
                [str(LMS_CLI), "unload", "--all"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                return False, f"Failed to unload models: {result.stderr[:100]}"
            logger.info("[lmstudio] Unloaded all models")
            time.sleep(1)  # Brief wait for unload to complete
        except subprocess.TimeoutExpired:
            return False, "Unload timed out"
        except Exception as e:
            return False, f"Unload error: {e}"
    else:
        logger.info("[lmstudio] No models loaded, loading: %s", target_model)

    # Load target model
    try:
        result = subprocess.run(
            [str(LMS_CLI), "load", "--yes", target_model],
            capture_output=True,
            text=True,
            timeout=90
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            if "not found" in stderr.lower() or "no model" in stderr.lower():
                return False, f"Model '{target_model}' not found - check .env LMSTUDIO_MODEL"
            return False, f"Load failed: {stderr[:200]}"

        # Verify load succeeded
        time.sleep(2)
        loaded = _get_loaded_models(base_url)
        if target_model in loaded:
            logger.info("[lmstudio] Successfully loaded: %s", target_model)
            return True, f"Loaded {target_model}"
        else:
            return False, f"Load succeeded but model not in list: {loaded}"

    except subprocess.TimeoutExpired:
        return False, f"Loading '{target_model}' timed out (>90s)"
    except FileNotFoundError:
        return False, "'lms' CLI not found - install LM Studio CLI"
    except Exception as e:
        return False, f"Load error: {e}"


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

    target_model = cfg.model or LMSTUDIO_MODEL
    if not target_model:
        raise SummarizerError("No model specified in config or .env LMSTUDIO_MODEL")

    # Ensure correct model is loaded (auto-load if needed, unload others)
    success, message = _ensure_correct_model_loaded(LMSTUDIO_BASE_URL, target_model)
    if not success:
        raise SummarizerError(f"Model setup failed: {message}")

    logger.debug("[lmstudio] %s", message)

    url = f"{LMSTUDIO_BASE_URL}/v1/chat/completions"
    payload = {
        "model": target_model,  # Use the verified loaded model
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_TOKENS,
        "temperature": cfg.temperature,
        "response_format": SUMMARY_JSON_SCHEMA,
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


def _validate_bullet_structure(bullets: List[str], raw_output: str) -> tuple[bool, str]:
    """Validate that bullets conform to required structure or accept prose fallback.

    Checks:
    - 3-4 structured bullets with required labels, OR
    - Coherent prose (100-2000 chars) as fallback

    Returns:
        (is_valid, error_message) where error_message is empty if valid
    """
    # Check for structured bullets (3-4 with labels)
    if 3 <= len(bullets) <= 4:
        # Check for required labels
        bullets_text = "\n".join(bullets)
        required_labels = ["**KEY FINDING**", "**TACTICAL WIN", "**MARKET SIGNAL", "**CONCERN**"]

        # Find which labels are present
        present_labels = [label for label in required_labels if label in bullets_text]
        missing_labels = [label for label in required_labels if label not in bullets_text]

        logger.debug("[validate][debug] Found %d bullets, checking labels - present: %s, missing: %s",
                     len(bullets), present_labels, missing_labels)

        if not missing_labels:
            return (True, "")

        # Has 3-4 bullets but missing labels - fall through to prose check

    # Check for prose fallback (coherent text without bullet structure)
    prose_length = len(raw_output.strip())
    if 100 <= prose_length <= 2000:
        logger.debug("[validate][debug] Accepting prose fallback (%d chars)", prose_length)
        return (True, "")

    # Neither structured bullets nor valid prose
    if len(bullets) < 3:
        return (False, f"Expected 3-4 bullets, got {len(bullets)}, and output not valid prose ({prose_length} chars)")
    elif len(bullets) > 4:
        return (False, f"Expected 3-4 bullets, got {len(bullets)}")
    else:
        return (False, f"Expected 3-4 bullets with required labels, got {len(bullets)} bullets with missing labels: {', '.join(missing_labels)}")


def _parse_actionability(raw_output: str) -> str:
    """Parse actionability from LLM output, trying JSON first then text fallback."""
    try:
        data = json.loads(raw_output)
        if "actionability" in data:
            act = data["actionability"]
            return f"{act['emoji']} {act['label']}"
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    # Fall back to text-based parsing
    return _parse_actionability_text(raw_output)


def _parse_actionability_text(raw_output: str) -> str:
    """Extract actionability indicator from text-formatted LLM output (legacy fallback).

    Looks for pattern: **ACTIONABILITY**: <emoji> <label>
    Returns the full actionability string if found, empty string otherwise.
    """
    actionability_match = re.search(r'\*\*ACTIONABILITY\*\*:\s*([^\n]+)', raw_output)
    if actionability_match:
        return actionability_match.group(1).strip()
    return ""


def _normalize_bullet_tags(bullet: str) -> str:
    """Normalize tag formatting in bullets to ensure consistency.

    Normalizes all tag variations to emoji-only format.
    """
    # Tag normalization mappings (text/full tags → emoji-only)
    tactical_mappings = {
        "SHIP NOW": "🚀",
        "ROADMAP": "🗺️",
        "WATCH": "👀",
    }

    market_mappings = {
        "URGENT": "🔴",
        "NOTABLE": "🟡",
        "CONTEXT": "⚫",
    }

    # Process bullet text
    result = bullet

    # Normalize tactical tags to emoji-only (case-insensitive)
    for base_tag, emoji in tactical_mappings.items():
        # Match [TAG], [emoji TAG], or [emoji] variations, case-insensitive
        pattern = r'\[(?:[^\]]*\s+)?' + re.escape(base_tag) + r'\]'
        if re.search(pattern, result, re.IGNORECASE):
            # Replace with emoji-only version
            result = re.sub(pattern, f'[{emoji}]', result, flags=re.IGNORECASE)

    # Normalize market signal tags to emoji-only (case-insensitive)
    for base_tag, emoji in market_mappings.items():
        pattern = r'\[(?:[^\]]*\s+)?' + re.escape(base_tag) + r'\]'
        if re.search(pattern, result, re.IGNORECASE):
            result = re.sub(pattern, f'[{emoji}]', result, flags=re.IGNORECASE)

    # Defensive fallback for placeholder tags (shouldn't occur with fixed prompt)
    placeholder_mappings = {
        '[action-tag]': '[🗺️]',
        '[urgency-tag]': '[🟡]',
        '[TAG]': '[🟡]',  # Handle literal [TAG] from malformed prompt
    }

    for placeholder, default_tag in placeholder_mappings.items():
        if placeholder in result:
            logger.warning("LLM generated placeholder tag: %s (replacing with %s)", placeholder, default_tag)
            result = result.replace(placeholder, default_tag)

    return result


def _parse_bullets(raw_output: str) -> List[str]:
    """Parse bullets from LLM output, trying JSON first then text fallback."""
    try:
        data = json.loads(raw_output)
        if "bullets" in data:
            return [f"**{b['label']}**: {b['text']}" for b in data["bullets"]]
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    # Fall back to text-based parsing
    return _parse_bullets_text(raw_output)


def _parse_bullets_text(output: str) -> List[str]:
    """Parse bullets from text-formatted LLM output (legacy fallback)."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    bullets: List[str] = []
    for line in lines:
        # Support ASCII markers (- *) and Unicode bullet (•)
        if line.startswith("- ") or line.startswith("* ") or line.startswith("• "):
            bullets.append(line[2:].strip())
        elif line and line[0].isdigit() and line[1:3] in {". ", ") "}:
            bullets.append(line[3:].strip())
    if not bullets and output:
        bullets = _sentence_split(output)

    # Normalize tags in all bullets
    bullets = [_normalize_bullet_tags(bullet) for bullet in bullets if bullet]
    return bullets


def _sentence_split(text: str) -> List[str]:
    """Split text into sentences, avoiding splits inside numbers/decimals.

    Fallback for when LLM doesn't return structured bullets.
    """
    sentences = []
    buffer = ""
    for i, char in enumerate(text):
        buffer += char
        if char in ".!?":
            # Don't split if period is inside a number (e.g., "0.74")
            next_char = text[i+1] if i+1 < len(text) else ""
            prev_char = text[i-1] if i > 0 else ""

            # Skip if surrounded by digits (decimal number)
            if prev_char.isdigit() and (next_char.isdigit() or next_char == ")"):
                continue

            cleaned = buffer.strip()
            if cleaned:
                sentences.append(cleaned)
            buffer = ""
    if buffer.strip():
        sentences.append(buffer.strip())
    return sentences[:4]  # Changed from 3 to 4 to match expected bullet count


__all__ = ["summarize_article", "SummarizerConfig", "SummarizerError"]
