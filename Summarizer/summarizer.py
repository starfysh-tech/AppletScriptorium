"""Interface for generating article summaries via Ollama."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any, Callable, List


class SummarizerError(RuntimeError):
    """Raised when summary generation fails."""


@dataclass(frozen=True)
class SummarizerConfig:
    model: str = "granite4:tiny-h"
    temperature: float = 0.1
    max_tokens: int = 256


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
    instructions = (
        "Write 3 concise bullet summaries capturing the most important clinical or operational insights from the article. "
        "Each bullet should stand alone, avoid repetition, and focus on practical takeaways."
    )
    return f"Title: {title}\n\nArticle content:\n{content_text}\n\n{instructions}"


def _run_with_ollama(prompt: str, cfg: SummarizerConfig) -> str:
    args = [
        "ollama",
        "run",
        cfg.model,
    ]

    process = subprocess.run(
        args,
        input=prompt,
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        raise SummarizerError(process.stderr.strip() or "unknown ollama error")
    return process.stdout.strip()


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
