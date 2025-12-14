"""Render summaries into HTML and plaintext digests."""
from __future__ import annotations

import html
import logging
import re
from datetime import datetime
from typing import Iterable, Sequence

logger = logging.getLogger(__name__)


def generate_executive_summary(articles: Iterable[dict]) -> list[str]:
    """Generate ultra-concise one-line summaries for each article, sorted by actionability.

    Extracts KEY FINDING from each article, sorts by actionability priority
    (🎯 ACT NOW → ⚠️ MONITOR → 🔍 RESEARCH NEEDED → ℹ️ CONTEXT ONLY),
    and prefixes each with the original article number for reference.
    """
    # Define actionability priority (lower = higher priority)
    actionability_priority = {
        '🎯': 0, 'ACT NOW': 0,
        '⚠️': 1, 'MONITOR': 1,
        '🔍': 2, 'RESEARCH NEEDED': 2, 'RESEARCH': 2,
        'ℹ️': 3, 'CONTEXT ONLY': 3, 'CONTEXT': 3,
    }

    def get_priority(article: dict) -> int:
        """Extract actionability priority from article summary bullets."""
        # First check if actionability is stored as a field
        actionability = article.get("actionability", "")
        if actionability:
            for key, priority in actionability_priority.items():
                if key in actionability.upper():
                    return priority

        # Fallback: look for ACTIONABILITY in summary bullets
        bullets = article.get("summary", [])
        for bullet in bullets:
            text = bullet.get("text", "")
            # Look for ACTIONABILITY line
            if "ACTIONABILITY" in text.upper():
                # Check for each priority tag
                for key, priority in actionability_priority.items():
                    if key in text.upper():
                        return priority
        return 4  # Unknown/missing actionability

    # Convert to list and preserve original indices
    article_list = list(articles)
    indexed_articles = [(idx, article) for idx, article in enumerate(article_list, 1)]

    # Sort by actionability priority (but keep original index)
    sorted_articles = sorted(indexed_articles, key=lambda x: get_priority(x[1]))

    summaries = []
    for original_idx, article in sorted_articles:
        bullets = article.get("summary", [])

        # Find first bullet (KEY FINDING, KEY DEVELOPMENT, ANNOUNCEMENT, or THESIS)
        first_bullet_labels = [
            "**KEY FINDING**:", "**KEY DEVELOPMENT**:", "**ANNOUNCEMENT**:", "**THESIS**:"
        ]
        key_finding = None
        for bullet in bullets:
            text = bullet.get("text", "")
            if any(label in text[:50] for label in first_bullet_labels):
                # Remove label prefix for cleaner summary
                key_finding = re.sub(r'\*\*[A-Z_ ]+\*\*:\s*', '', text)
                break

        if not key_finding and bullets:
            # Fallback to first bullet
            key_finding = bullets[0].get("text", "")
            # Remove any bold label prefix
            key_finding = re.sub(r'\*\*[A-Z_ ]+\*\*:\s*', '', key_finding)

        if key_finding:
            # Word-only truncation at 50 words max (avoids splitting on abbreviations like "Inc.")
            words = key_finding.split()
            if len(words) > 50:
                summary = " ".join(words[:50]) + '...'
            else:
                summary = key_finding.rstrip('.,;:')

            # Prefix with original article number
            summaries.append(f"[{original_idx}] {summary}")

    return summaries


def generate_cross_article_insights(articles: list[dict]) -> list[str]:
    """Generate cross-article insights using LLM to identify patterns and themes.

    Uses LM Studio (or Ollama fallback) to analyze article titles + KEY FINDING bullets
    and identify recurring themes, methodological patterns, and knowledge gaps.

    Falls back gracefully if LLM unavailable - insights are optional enhancement.
    """
    from urllib.parse import urlparse

    insights = []
    article_list = list(articles)

    if len(article_list) < 2:
        return insights

    # Import config constants
    try:
        from .config import (
            CROSS_ARTICLE_INSIGHTS_PROMPT,
            CROSS_ARTICLE_MIN_ARTICLES,
            CROSS_ARTICLE_MIN_SOURCES,
            LMSTUDIO_MODEL,
            TEMPERATURE,
        )
    except ImportError as exc:
        logger.warning("[insights] Could not import config: %s", exc)
        return []

    # Apply quality gates
    if len(article_list) < CROSS_ARTICLE_MIN_ARTICLES:
        logger.info(
            "[insights] Skipping insights: only %d articles (minimum: %d)",
            len(article_list),
            CROSS_ARTICLE_MIN_ARTICLES
        )
        return insights

    # Extract unique source domains
    unique_sources = set()
    for article in article_list:
        url = article.get("url", "")
        if url:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Strip www. prefix for normalization
            if domain.startswith("www."):
                domain = domain[4:]
            unique_sources.add(domain)

    if len(unique_sources) < CROSS_ARTICLE_MIN_SOURCES:
        logger.info(
            "[insights] Skipping insights: only %d unique sources (minimum: %d)",
            len(unique_sources),
            CROSS_ARTICLE_MIN_SOURCES
        )
        return insights

    # Build compact summaries (title + KEY FINDING only for token efficiency)
    summaries_text = []
    for idx, article in enumerate(article_list, 1):
        title = article.get("title", "")[:80]  # Truncate long titles
        bullets = article.get("summary", [])

        # Extract KEY FINDING bullet
        key_finding = next(
            (b.get("text", "") for b in bullets if "KEY FINDING" in b.get("text", "")),
            bullets[0].get("text", "") if bullets else ""
        )

        summaries_text.append(f"[{idx}] {title}\n    {key_finding}")

    # Import LLM infrastructure (done inside function to avoid circular imports)
    try:
        from .summarizer import SummarizerConfig, SummarizerError, _run_with_lmstudio

        prompt = CROSS_ARTICLE_INSIGHTS_PROMPT.format(
            count=len(article_list),
            article_summaries="\n\n".join(summaries_text)
        )

        # Use higher temperature than summarization for creative pattern-finding
        # Must explicitly set model to use LM Studio model (not default Ollama model)
        cfg = SummarizerConfig(model=LMSTUDIO_MODEL, temperature=0.3, max_tokens=1024)

        logger.info("[insights] Generating cross-article insights for %d articles", len(article_list))

        try:
            raw_output = _run_with_lmstudio(prompt, cfg)

            # Parse insights (one per line starting with "- ")
            for line in raw_output.strip().split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    insights.append(line[2:])  # Remove "- " prefix

            logger.info("[insights] Generated %d insights", len(insights))
            return insights[:5]  # Limit to top 5

        except SummarizerError as exc:
            logger.warning("[insights] LLM-based generation failed: %s", exc)
            return []  # Fail gracefully - insights are optional

    except ImportError as exc:
        logger.warning("[insights] Could not import LLM infrastructure: %s", exc)
        return []


def _split_title_and_source(title: str) -> tuple[str, str]:
    """Split title into main title and source suffix.

    Extracts common source suffixes (e.g., " - medRxiv", " | Author - LinkedIn")
    and returns them separately for consistent rendering.

    Returns:
        (main_title, source_suffix) where source_suffix includes leading separator
        or (title, "") if no recognizable source pattern found
    """
    # Patterns for common source suffixes (order matters - most specific first)
    patterns = [
        r'(\s+\|[^|]+?(?:PhD|MD|MBA|MSc|BSc).* - LinkedIn)$',  # | Author Name, Credentials - LinkedIn
        r'(\s+\|\s*[A-Za-z0-9\s]+)$',  # Generic " | Publisher" pattern
        r'(\s+- medRxiv)$',
        r'(\s+- ASCO Publications)$',
        r'(\s+- PubMed)$',
        r'(\s+- Nature)$',
        r'(\s+- Science)$',
        r'(\s+- The Lancet)$',
        r'(\s+- BMJ)$',
        r'(\s+- JAMA)$',
    ]

    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            source_suffix = match.group(1)
            main_title = title[:match.start()]
            return (main_title, source_suffix)

    return (title, "")


def _format_header_stats(articles: list[dict]) -> str:
    """Format article count and source diversity for header."""
    count = len(articles)
    if count == 0:
        return ""

    # Count unique publishers/sources
    sources = set()
    for article in articles:
        publisher = article.get("publisher", "")
        if publisher:
            sources.add(publisher.lower())

    source_count = len(sources) or 1  # At least 1 source if we have articles

    article_word = "article" if count == 1 else "articles"
    source_word = "source" if source_count == 1 else "sources"

    return f" • {count} {article_word} from {source_count} {source_word}"


def render_digest_html(articles: Iterable[dict], *, generated_at: datetime | None = None, missing: Sequence[dict] | None = None, topic: str | None = None) -> str:
    generated_at = generated_at or datetime.now()
    missing = missing or []
    article_list = list(articles)
    topic_text = f": {topic}" if topic else ""
    header_stats = _format_header_stats(article_list)

    # Generate executive summary section (skip for single articles - redundant)
    exec_block = ""
    if len(article_list) >= 2:
        exec_summaries = generate_executive_summary(article_list)
        if exec_summaries:
            exec_items = "\n".join(f"    <li>{html.escape(summary)}</li>" for summary in exec_summaries)
            exec_block = (
                "<section class=\"summary\">\n"
                "  <h2>Summary of today's articles</h2>\n"
                "  <ul>\n"
                f"{exec_items}\n"
                "  </ul>\n"
                "</section>\n"
            )

    # Generate cross-article insights section
    insights = generate_cross_article_insights(article_list)
    insights_block = ""
    if insights:
        insight_items = "\n".join(f"    <li>{html.escape(insight)}</li>" for insight in insights)
        insights_block = (
            "<section class=\"insights\">\n"
            "  <h2>📊 Cross-Article Insights</h2>\n"
            "  <ul>\n"
            f"{insight_items}\n"
            "  </ul>\n"
            "</section>\n"
        )

    # Generate article blocks
    article_blocks = []
    for article in article_list:
        raw_title = article.get("title", "")
        main_title, source_suffix = _split_title_and_source(raw_title)

        # If no source in title, use publisher metadata as source
        if not source_suffix:
            publisher_name = article.get("publisher", "")
            if publisher_name:
                source_suffix = f" - {publisher_name}"

        title_html = html.escape(main_title)
        source_html = html.escape(source_suffix) if source_suffix else ""
        url = article.get("url") or ""
        publisher = html.escape(article.get("publisher") or "")
        snippet = html.escape(article.get("snippet") or "")
        bullets = article.get("summary", [])
        lines = []
        for block in bullets[:4]:  # Show all 4 bullets
            text = block.get("text", "")
            if text:
                # Parse **LABEL**: format and make labels bold
                # Convert **LABEL**: to <b>LABEL:</b>
                text_html = re.sub(r'\*\*(.*?)\*\*:', r'<b>\1:</b>', text)
                text_html = html.escape(text_html)
                # Unescape the b tags we just added
                text_html = text_html.replace('&lt;b&gt;', '<b>').replace('&lt;/b&gt;', '</b>')
                lines.append(f"<li>{text_html}</li>")
        lines_html = "\n".join(lines)
        meta_line = " • ".join(filter(None, [publisher, snippet]))
        meta_html = f"<p class=\"meta\">{meta_line}</p>" if meta_line else ""

        # Add actionability indicator if present
        actionability = article.get("actionability", "")
        actionability_html = ""
        if actionability:
            actionability_html = f"  <p class=\"actionability\">{html.escape(actionability)}</p>\n"

        article_blocks.append(
            f"<article>\n"
            f"  <h2><a href=\"{html.escape(url)}\">{title_html}</a>{source_html}</h2>\n"
            f"  {meta_html}\n"
            f"  <ul>\n{lines_html}\n  </ul>\n"
            f"{actionability_html}"
            f"</article>"
        )

    missing_block = ""
    if missing:
        items = "\n".join(
            f"    <li><a href=\"{html.escape(item.get('url', ''))}\">{html.escape(item.get('url', ''))}</a> — {html.escape(item.get('reason', ''))}</li>"
            for item in missing
        )
        missing_block = (
            "<section class=\"missing\">\n"
            "  <h2>Missing articles</h2>\n"
            "  <ul>\n"
            f"{items}\n"
            "  </ul>\n"
            "</section>"
        )

    inner = "\n".join(article_blocks)
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "  <meta charset=\"utf-8\" />\n"
        f"  <title>Google Alert Intelligence{topic_text}</title>\n"
        "  <style>\n"
        "    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 2rem; color: #222; }\n"
        "    header { margin-bottom: 2rem; }\n"
        "    section { margin-bottom: 2rem; background: #f5f5f5; padding: 1rem; border-radius: 0.5rem; }\n"
        "    section h2 { margin-top: 0; font-size: 1.1rem; color: #333; }\n"
        "    section ul { margin-bottom: 0; }\n"
        "    article { margin-bottom: 2rem; }\n"
        "    article h2 { margin-bottom: 0.5rem; font-size: 1.25rem; }\n"
        "    article ul { margin-top: 0.5rem; }\n"
        "    article li b { color: #0066cc; font-weight: bold; }\n"
        "    .meta { color: #666; font-size: 0.9rem; margin: 0; }\n"
        "    .actionability { color: #333; font-weight: bold; font-size: 0.95rem; margin-top: 0.5rem; margin-bottom: 0; padding: 0.5rem; background: #e8f4f8; border-left: 3px solid #0066cc; }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        f"<header><h1>Google Alert Intelligence{topic_text}</h1><p>{generated_at:%B %d, %Y}{header_stats}</p></header>\n"
        f"{exec_block}\n"
        f"{insights_block}\n"
        f"{inner}\n"
        f"{missing_block}\n"
        "</body>\n"
        "</html>\n"
    )


def render_digest_text(articles: Iterable[dict], *, generated_at: datetime | None = None, missing: Sequence[dict] | None = None, topic: str | None = None) -> str:
    generated_at = generated_at or datetime.now()
    missing = missing or []
    article_list = list(articles)
    topic_text = f": {topic}" if topic else ""
    header_stats = _format_header_stats(article_list)

    lines = [f"Google Alert Intelligence{topic_text} — {generated_at:%B %d, %Y}{header_stats}", ""]

    # Add executive summary (skip for single articles - redundant)
    if len(article_list) >= 2:
        exec_summaries = generate_executive_summary(article_list)
        if exec_summaries:
            lines.append("Summary of today's articles:")
            for summary in exec_summaries:
                lines.append(f"- {summary}")
            lines.append("")

    # Add cross-article insights
    insights = generate_cross_article_insights(article_list)
    if insights:
        lines.append("📊 Cross-Article Insights:")
        for insight in insights:
            lines.append(f"- {insight}")
        lines.append("")

    # Add full articles
    for article in article_list:
        raw_title = article.get("title", "")
        main_title, source_suffix = _split_title_and_source(raw_title)

        # If no source in title, use publisher metadata as source
        if not source_suffix:
            publisher_name = article.get("publisher", "")
            if publisher_name:
                source_suffix = f" - {publisher_name}"

        title = main_title + source_suffix  # Recombine for plaintext (no HTML formatting)
        url = article.get("url") or ""
        publisher = article.get("publisher", "")
        snippet = article.get("snippet", "")
        bullets = article.get("summary", [])
        lines.append(title)
        if publisher or snippet:
            lines.append("  " + " • ".join(filter(None, [publisher, snippet])))
        if url:
            lines.append(f"  {url}")
        for block in bullets[:4]:  # Show all 4 bullets
            text = block.get("text", "")
            if text:
                lines.append(f"    - {text}")

        # Add actionability indicator if present
        actionability = article.get("actionability", "")
        if actionability:
            lines.append(f"    ACTIONABILITY: {actionability}")

        lines.append("")
    if missing:
        lines.append("Missing articles")
        for item in missing:
            url = item.get("url", "")
            reason = item.get("reason", "")
            line = f"- {url}"
            if reason:
                line += f" — {reason}"
            lines.append(line)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


__all__ = ["render_digest_html", "render_digest_text"]
