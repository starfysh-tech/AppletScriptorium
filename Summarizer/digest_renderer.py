"""Render summaries into HTML and plaintext digests."""
from __future__ import annotations

import html
from datetime import datetime
from typing import Iterable

SUMMARY_COUNT = 3


def render_digest_html(articles: Iterable[dict], *, generated_at: datetime | None = None) -> str:
    generated_at = generated_at or datetime.now()
    article_blocks = []

    for article in articles:
        title = html.escape(article.get("title", ""))
        url = article.get("url") or ""
        publisher = html.escape(article.get("publisher", ""))
        snippet = html.escape(article.get("snippet", ""))
        bullets = article.get("summary", [])
        lines = []
        for block in bullets[:SUMMARY_COUNT]:
            text = html.escape(block.get("text", ""))
            if text:
                lines.append(f"<li>{text}</li>")
        lines_html = "\n".join(lines)
        meta_line = " • ".join(filter(None, [publisher, snippet]))
        meta_html = f"<p class=\"meta\">{meta_line}</p>" if meta_line else ""
        article_blocks.append(
            f"<article>\n"
            f"  <h2><a href=\"{html.escape(url)}\">{title}</a></h2>\n"
            f"  {meta_html}\n"
            f"  <ul>\n{lines_html}\n  </ul>\n"
            f"</article>"
        )

    inner = "\n".join(article_blocks)
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "  <meta charset=\"utf-8\" />\n"
        "  <title>PRO Alert Digest</title>\n"
        "  <style>\n"
        "    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 2rem; color: #222; }\n"
        "    header { margin-bottom: 2rem; }\n"
        "    article { margin-bottom: 2rem; }\n"
        "    article h2 { margin-bottom: 0.5rem; font-size: 1.25rem; }\n"
        "    article ul { margin-top: 0.5rem; }\n"
        "    .meta { color: #666; font-size: 0.9rem; margin: 0; }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        f"<header><h1>PRO Alert Digest</h1><p>{generated_at:%B %d, %Y}</p></header>\n"
        f"{inner}\n"
        "</body>\n"
        "</html>\n"
    )


def render_digest_text(articles: Iterable[dict], *, generated_at: datetime | None = None) -> str:
    generated_at = generated_at or datetime.now()
    lines = [f"PRO Alert Digest — {generated_at:%B %d, %Y}", ""]
    for article in articles:
        title = article.get("title", "")
        url = article.get("url") or ""
        publisher = article.get("publisher", "")
        snippet = article.get("snippet", "")
        bullets = article.get("summary", [])
        lines.append(title)
        if publisher or snippet:
            lines.append("  " + " • ".join(filter(None, [publisher, snippet])))
        if url:
            lines.append(f"  {url}")
        for block in bullets[:SUMMARY_COUNT]:
            text = block.get("text", "")
            if text:
                lines.append(f"    - {text}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


__all__ = ["render_digest_html", "render_digest_text"]
