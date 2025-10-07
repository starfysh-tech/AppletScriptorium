"""Convert article HTML into Markdown-friendly plaintext."""
from __future__ import annotations

from typing import Iterable

from bs4 import BeautifulSoup
from markdownify import markdownify as md

try:
    from readability import Document  # type: ignore
except ImportError:  # pragma: no cover - readability optional
    Document = None  # type: ignore


_STRIP_TAGS: Iterable[str] = ("script", "style", "nav", "footer", "header")


def extract_content(html: str) -> str:
    """Return a cleaned Markdown string for the article body."""
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


__all__ = ["extract_content"]
