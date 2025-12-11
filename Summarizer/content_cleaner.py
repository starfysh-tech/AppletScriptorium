"""Convert article HTML into Markdown-friendly plaintext."""
from __future__ import annotations

import re
from typing import Iterable

from bs4 import BeautifulSoup
from markdownify import markdownify as md

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


def extract_content(html: str) -> str:
    """Return a cleaned Markdown string for the article body."""
    # TODO: Investigate why medrxiv.org domain extracts metadata (author names, DOI)
    # instead of article content. May need domain-specific extraction rules or
    # better readability configuration for preprint servers.

    # Sanitize HTML before passing to readability to prevent lxml errors
    html = _sanitize_html(html)

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
    lines = [line.rstrip() for line in markdown.splitlines()]
    filtered = [line for line in lines if line.strip()]
    return "\n".join(filtered)


__all__ = ["extract_content", "strip_cruft"]
