"""Convert article HTML into Markdown-friendly plaintext."""
from __future__ import annotations

import logging
import re
from typing import Iterable

from bs4 import BeautifulSoup
from markdownify import markdownify as md

from .quality_checks import is_low_quality

logger = logging.getLogger(__name__)

try:
    from readability import Document  # type: ignore
except ImportError:  # pragma: no cover - readability optional
    Document = None  # type: ignore


_STRIP_TAGS: Iterable[str] = ("script", "style", "nav", "footer", "header")

# Compiled regex patterns for cruft detection
_CRUFT_PATTERNS = [
    re.compile(r'^\[Google Scholar\]\(https?://scholar\.google\.com/[^\)]+\)$'),
    re.compile(r'^<https?://[^\s>]+>$'),
    re.compile(r'^\d+\.\s+.*\[Google Scholar\].*$'),
    re.compile(r'^https://doi\.org/\S+$'),
]


def _sanitize_html(html: str) -> str:
    """Remove NULL bytes and control characters that break lxml parsing.

    lxml requires XML-compatible strings: Unicode or ASCII with no NULL bytes
    or control characters (except tab, newline, carriage return).
    """
    # Remove NULL bytes
    html = html.replace('\x00', '')

    # Remove control characters except \t (0x09), \n (0x0A), \r (0x0D)
    # Pattern matches \x01-\x08, \x0B-\x0C, \x0E-\x1F
    html = re.sub(r'[\x01-\x08\x0B-\x0C\x0E-\x1F]', '', html)

    return html


def strip_cruft(markdown: str) -> str:
    """Remove cruft lines from markdown content.

    Removes:
    - Google Scholar links
    - Standalone URLs in angle brackets
    - Reference entries containing Google Scholar
    - DOI lines

    Args:
        markdown: Markdown text to clean

    Returns:
        Cleaned markdown with cruft lines removed
    """
    lines = markdown.splitlines()
    kept_lines = []

    for line in lines:
        stripped = line.strip()
        # Check if line matches any cruft pattern
        is_cruft = any(pattern.match(stripped) for pattern in _CRUFT_PATTERNS)
        if not is_cruft:
            kept_lines.append(line)

    return "\n".join(kept_lines)


def extract_content(html: str, url: str = "") -> str:
    """Return cleaned Markdown for the article body.

    Uses trafilatura as primary extractor (better UI element handling),
    falls back to readability-lxml if trafilatura fails or returns insufficient content.
    """
    # Sanitize HTML before passing to extractors to prevent lxml errors
    html = _sanitize_html(html)

    # Try trafilatura first (handles UI elements better than readability-lxml)
    try:
        import trafilatura
        content = trafilatura.extract(
            html,
            url=url,
            include_links=False,
            include_images=False,
            include_tables=True,
            output_format="markdown",
            favor_recall=True,
        )
        word_count = len(content.split()) if content else 0

        # Accept trafilatura if sufficient content and passes quality check
        if word_count >= 100 and not is_low_quality(content):
            logger.debug("[extract] trafilatura succeeded (%d words)", word_count)
            return _clean_extracted_text(content)
        else:
            reason = "insufficient" if word_count < 100 else "low quality"
            logger.debug("[extract] trafilatura rejected (%s, %d words), trying readability", reason, word_count)
    except Exception as exc:
        logger.debug("[extract] trafilatura failed (%s), trying readability", exc)

    # Fallback: readability-lxml (original implementation)
    main_html = html
    if Document is not None:
        try:
            main_html = Document(html).summary(html_partial=True)
        except Exception:  # pragma: no cover - readability edge cases
            main_html = html

    soup = BeautifulSoup(main_html, "html.parser")
    for tag_name in _STRIP_TAGS:
        for node in soup.find_all(tag_name):
            node.decompose()

    markdown = md(
        str(soup),
        strip=_STRIP_TAGS,
        heading_style="ATX",
    )
    result = _clean_extracted_text(markdown)
    logger.debug("[extract] readability-lxml returned (%d words)", len(result.split()))
    return result


def _clean_extracted_text(text: str) -> str:
    """Clean up extracted text (shared by both extractors)."""
    lines = [line.rstrip() for line in text.splitlines()]
    filtered = [line for line in lines if line.strip()]
    return "\n".join(filtered)


__all__ = ["extract_content", "strip_cruft"]
