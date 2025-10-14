"""Render summaries into HTML and plaintext digests."""
from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Iterable, Sequence


def generate_executive_summary(articles: Iterable[dict]) -> list[str]:
    """Generate ultra-concise one-line summaries for each article.

    Extracts KEY FINDING from each article as a metric-focused one-liner (10-15 words).
    """
    summaries = []
    for article in articles:
        bullets = article.get("summary", [])

        # Find KEY FINDING bullet
        key_finding = None
        for bullet in bullets:
            text = bullet.get("text", "")
            if text.startswith("**KEY FINDING**:") or "KEY FINDING" in text[:30]:
                # Remove label
                key_finding = re.sub(r'\*\*KEY FINDING\*\*:\s*', '', text, flags=re.IGNORECASE)
                break

        if not key_finding and bullets:
            # Fallback to first bullet
            key_finding = bullets[0].get("text", "")

        if key_finding:
            # Extract first sentence or key metric, target 10-15 words
            # Split on sentence boundaries
            sentences = re.split(r'[.;]', key_finding)
            first_part = sentences[0].strip() if sentences else key_finding

            # Truncate to ~15 words for executive summary
            words = first_part.split()
            if len(words) > 15:
                summary = " ".join(words[:15])
            else:
                summary = first_part

            # Clean up trailing punctuation
            summary = summary.rstrip('.,;:')
            summaries.append(summary)

    return summaries


def generate_cross_article_insights(articles: list[dict]) -> list[str]:
    """Extract actionable patterns and themes across multiple articles.

    Returns insights with specific evidence (e.g., "COMPLETION CHALLENGE: 3 studies show 19-31% rates").
    """
    insights = []
    article_list = list(articles)

    if len(article_list) < 2:
        return insights

    # Extract structured findings from each article
    completion_rates = []
    clinical_validity = []
    regulatory_mentions = []

    for article in article_list:
        title = article.get("title", "")
        for bullet in article.get("summary", []):
            text = bullet.get("text", "")
            text_lower = text.lower()

            # Extract completion/adherence rates
            completion_match = re.search(r'(\d+(?:\.\d+)?%)\s*(?:completion|adherence|engagement)', text_lower)
            if completion_match:
                completion_rates.append(completion_match.group(1))

            # Track clinical validity claims (predict mortality, outcomes)
            if re.search(r'predict.{0,30}(mortality|outcome|hospital)', text_lower):
                clinical_validity.append(title[:30])

            # Track regulatory pressure mentions
            if re.search(r'(fda|regulator|regulatory).{0,30}(require|mandate|guideline|endpoint)', text_lower):
                regulatory_mentions.append(title[:40])

    # Generate insights from patterns
    if len(completion_rates) >= 2:
        # Sort and format completion rates
        rates = sorted(set(completion_rates))
        if len(rates) >= 2:
            rate_range = f"{rates[0]}-{rates[-1]}" if len(rates) > 1 else rates[0]
            insights.append(f"COMPLETION CHALLENGE: {len(completion_rates)} articles report {rate_range} ePRO completion/adherence rates")

    if len(clinical_validity) >= 2:
        insights.append(f"CLINICAL VALIDITY: PROs predict mortality/outcomes in {len(clinical_validity)} studies ({', '.join(clinical_validity[:2])}...)")

    if len(regulatory_mentions) >= 2:
        insights.append(f"REGULATORY PRESSURE: {len(regulatory_mentions)} articles cite FDA/regulatory emphasis on PRO data integration")

    # Look for common intervention patterns
    intervention_keywords = [
        ("reminder", "automated reminders"),
        ("dashboard", "dashboard/visualization tools"),
        ("ehr integration", "EHR integration"),
        ("mobile", "mobile/app-based delivery")
    ]

    for keyword, label in intervention_keywords:
        count = sum(1 for article in article_list
                   for bullet in article.get("summary", [])
                   if keyword in bullet.get("text", "").lower())
        if count >= 2:
            insights.append(f"IMPLEMENTATION PATTERN: {count} articles mention {label} as tactical approach")
            break  # Only report most common pattern

    # Limit to top 5 most actionable insights
    return insights[:5]


def render_digest_html(articles: Iterable[dict], *, generated_at: datetime | None = None, missing: Sequence[dict] | None = None) -> str:
    generated_at = generated_at or datetime.now()
    missing = missing or []
    article_list = list(articles)

    # Generate executive summary section
    exec_summaries = generate_executive_summary(article_list)
    exec_block = ""
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
        title = html.escape(article.get("title", ""))
        url = article.get("url") or ""
        publisher = html.escape(article.get("publisher", ""))
        snippet = html.escape(article.get("snippet", ""))
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
        article_blocks.append(
            f"<article>\n"
            f"  <h2><a href=\"{html.escape(url)}\">{title}</a></h2>\n"
            f"  {meta_html}\n"
            f"  <ul>\n{lines_html}\n  </ul>\n"
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
        "  <title>PRO Alert Digest</title>\n"
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
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        f"<header><h1>PRO Alert Digest</h1><p>{generated_at:%B %d, %Y}</p></header>\n"
        f"{exec_block}\n"
        f"{insights_block}\n"
        f"{inner}\n"
        f"{missing_block}\n"
        "</body>\n"
        "</html>\n"
    )


def render_digest_text(articles: Iterable[dict], *, generated_at: datetime | None = None, missing: Sequence[dict] | None = None) -> str:
    generated_at = generated_at or datetime.now()
    missing = missing or []
    article_list = list(articles)

    lines = [f"PRO Alert Digest — {generated_at:%B %d, %Y}", ""]

    # Add executive summary
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
        for block in bullets[:4]:  # Show all 4 bullets
            text = block.get("text", "")
            if text:
                lines.append(f"    - {text}")
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
