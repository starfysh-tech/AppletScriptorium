"""Utilities for extracting article links and metadata from Google Alert emails.

IMPORTANT: This module is optimized for Google Alert email format, which uses
www.google.com/url redirect links with target URLs in query parameters.

For other email formats (newsletters, RSS digests, etc.), implement separate
extractors following the same LinkRecord interface for composability.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class LinkRecord:
    """Represents a single article entry extracted from the alert."""

    title: str
    url: str
    publisher: Optional[str] = None
    snippet: Optional[str] = None

    def as_tsv_row(self) -> str:
        fields = [self.title, self.url, self.publisher or "", self.snippet or ""]
        return "\t".join(_sanitize(field) for field in fields)

    def to_dict(self) -> dict[str, str]:
        return {key: value for key, value in asdict(self).items() if value}


class UnsupportedInputError(ValueError):
    """Raised when the extractor cannot determine how to parse a file."""


def read_html_from_eml(eml_path: Path) -> str:
    """Parse a `.eml` file and return the decoded HTML part."""
    with eml_path.open("rb") as handle:
        message = BytesParser(policy=policy.default).parse(handle)

    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/html":
                return part.get_content()
    elif message.get_content_type() == "text/html":
        return message.get_content()

    raise UnsupportedInputError(f"No HTML part found in {eml_path}")


def extract_links_from_html(html: str) -> List[LinkRecord]:
    """Extract article titles, URLs, and metadata from the alert HTML body.

    Handles both direct Google Alerts and forwarded alert emails by searching
    for Google redirect links throughout the entire HTML, including within
    forwarded message sections (gmail_quote divs, etc.).

    Prioritizes schema.org Article containers (finds ALL articles with proper titles),
    with fallback to JSON metadata and DOM traversal for older email formats.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Try schema.org Article containers first (finds ALL articles with proper titles)
    records = _extract_from_schema_articles(soup)
    if records:
        return records

    # Fallback to JSON metadata (older format, limited to highlighted articles)
    json_records = _extract_from_json_metadata(soup)
    if json_records:
        return json_records

    # Final fallback to DOM traversal
    return _extract_from_dom(soup)


def _extract_from_schema_articles(soup: BeautifulSoup) -> List[LinkRecord]:
    """Extract articles from schema.org Article containers.

    Google Alerts structure each article as: <tr itemtype="http://schema.org/Article">
    This method finds ALL articles with proper titles from itemprop="name", avoiding
    the empty-title bug in DOM extraction where image-wrapping anchors have no text.
    """
    records: List[LinkRecord] = []
    seen_urls: set[str] = set()

    for article in soup.select('tr[itemtype="http://schema.org/Article"]'):
        # Get title from itemprop="name" (most reliable)
        name_elem = article.select_one('[itemprop="name"]')
        title = name_elem.get_text(" ", strip=True) if name_elem else ""

        # Get URL from any anchor with Google redirect
        url = None
        for anchor in article.select('a[href*="google.com/url"]'):
            url = _extract_canonical_url(anchor.get("href", ""))
            if url:
                break

        if not url or url in seen_urls:
            continue

        # Fallback: get title from anchor text if itemprop missing
        if not title:
            for anchor in article.select('a[href*="google.com/url"]'):
                anchor_text = anchor.get_text(" ", strip=True)
                if anchor_text:
                    title = anchor_text
                    break

        publisher = _extract_publisher(article)
        snippet = _extract_snippet(article)

        records.append(LinkRecord(title=title, url=url, publisher=publisher, snippet=snippet))
        seen_urls.add(url)

    return records


def _extract_from_json_metadata(soup: BeautifulSoup) -> List[LinkRecord]:
    """Extract article metadata from embedded JSON in Google Alert emails.

    Google Alerts include structured metadata in a <script type="application/json">
    tag with article titles, descriptions, and URLs in cards[].widgets[].

    Publisher info is extracted from title suffix first, with DOM fallback for
    alerts that don't include publisher in the title.
    """
    script = soup.select_one('script[type="application/json"][data-scope="inboxmarkup"]')
    if not script or not script.string:
        return []

    try:
        data = json.loads(script.string)
    except (json.JSONDecodeError, TypeError):
        return []

    # Build URL->publisher mapping from DOM for fallback
    url_to_publisher = _build_url_publisher_map(soup)

    records: List[LinkRecord] = []
    seen_urls: set[str] = set()

    # Navigate to widgets in cards
    cards = data.get("cards", [])
    for card in cards:
        widgets = card.get("widgets", [])
        for widget in widgets:
            if widget.get("type") != "LINK":
                continue

            title = widget.get("title", "")
            description = widget.get("description", "")
            google_url = widget.get("url", "")

            # Extract canonical URL from Google redirect
            canonical_url = _extract_canonical_url(google_url)
            if not canonical_url or canonical_url in seen_urls:
                continue

            # Extract publisher: try title suffix first, then DOM fallback
            publisher = _extract_publisher_from_title(title)
            if not publisher:
                publisher = url_to_publisher.get(canonical_url)

            records.append(LinkRecord(
                title=title,
                url=canonical_url,
                publisher=publisher,
                snippet=description
            ))
            seen_urls.add(canonical_url)

    return records


def _build_url_publisher_map(soup: BeautifulSoup) -> dict[str, str]:
    """Build mapping from article URLs to publisher names from DOM.

    Scans anchor tags with Google redirect URLs and extracts publisher info
    from nearby itemprop="publisher" elements.
    """
    url_to_publisher: dict[str, str] = {}

    for anchor in soup.select('a[href*="google.com/url"]'):
        href = anchor.get("href", "")
        canonical_url = _extract_canonical_url(href)
        if not canonical_url:
            continue

        # Search parent containers for publisher info
        container = anchor.find_parent('td') or anchor.find_parent('div') or anchor
        publisher = _extract_publisher(container)
        if publisher:
            url_to_publisher[canonical_url] = publisher

    return url_to_publisher


def _extract_canonical_url(google_url: str) -> Optional[str]:
    """Extract the real article URL from a Google redirect URL."""
    parsed = urlparse(google_url)
    if parsed.netloc != "www.google.com" or parsed.path != "/url":
        return None

    params = parse_qs(parsed.query)
    target = params.get("url") or params.get("q") or params.get("u")
    return target[0] if target else None


def _extract_publisher_from_title(title: str) -> Optional[str]:
    """Extract publisher name from title suffix patterns like 'Article | Publisher'."""
    # Common patterns: " - Publisher", " | Publisher", " – Publisher"
    for sep in (" | ", " - ", " – ", " — "):
        if sep in title:
            parts = title.rsplit(sep, 1)
            if len(parts) == 2 and parts[1].strip():
                return parts[1].strip()
    return None


def _extract_from_dom(soup: BeautifulSoup) -> List[LinkRecord]:
    """Fallback: Extract article metadata by traversing DOM structure."""
    records: List[LinkRecord] = []
    seen_urls: set[str] = set()

    for anchor in soup.select('a[href]'):
        href = anchor.get("href")
        if not href:
            continue

        parsed = urlparse(href)
        if parsed.netloc != "www.google.com" or parsed.path != "/url":
            # Skip feedback links, unsubscribe links, and other non-article chrome.
            continue

        params = parse_qs(parsed.query)
        target = params.get("url") or params.get("q") or params.get("u")
        if not target:
            continue
        canonical_url = target[0]
        if canonical_url in seen_urls:
            continue

        # For metadata, search up the tree for structured data containers
        metadata_container = anchor.find_parent('td') or anchor.find_parent('div') or anchor
        publisher = _extract_publisher(metadata_container)
        snippet = _extract_snippet(metadata_container)
        title = anchor.get_text(" ", strip=True)

        records.append(LinkRecord(title=title, url=canonical_url, publisher=publisher, snippet=snippet))
        seen_urls.add(canonical_url)

    return records


def extract_links_from_eml(eml_path: Path) -> List[LinkRecord]:
    """Convenience wrapper to extract links directly from an `.eml` file."""
    html = read_html_from_eml(eml_path)
    return extract_links_from_html(html)


def write_links_tsv(records: Sequence[LinkRecord], output_path: Path) -> None:
    output = "\n".join(record.as_tsv_row() for record in records)
    output_path.write_text(output + ("\n" if output else ""), encoding="utf-8")


def write_links_json(records: Sequence[LinkRecord], output_path: Path) -> None:
    output_path.write_text(json.dumps([record.to_dict() for record in records], indent=2) + "\n", encoding="utf-8")


def _infer_records(path: Path) -> Iterable[LinkRecord]:
    suffix = path.suffix.lower()
    if suffix == ".eml":
        return extract_links_from_eml(path)
    if suffix in {".html", ".htm"}:
        html = path.read_text(encoding="utf-8")
        return extract_links_from_html(html)
    raise UnsupportedInputError(f"Unsupported file type for {path}")


def _extract_publisher(container) -> Optional[str]:
    node = container.select_one('[itemprop="publisher"] [itemprop="name"]') if hasattr(container, 'select_one') else None
    return _sanitize(node.get_text(" ", strip=True)) if node else None


def _extract_snippet(container) -> Optional[str]:
    node = container.select_one('[itemprop="description"]') if hasattr(container, 'select_one') else None
    return _sanitize(node.get_text(" ", strip=True)) if node else None


def _sanitize(value: str) -> str:
    return " ".join(value.replace("\t", " ").split())


def run_cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract link/title metadata from a Google Alert export.")
    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to the alert `.html` or `.eml` file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output path. Writes TSV/JSON when provided; otherwise prints to stdout.",
    )
    parser.add_argument(
        "--format",
        choices=("tsv", "json"),
        default="tsv",
        help="Output format (defaults to TSV).",
    )
    args = parser.parse_args(argv)

    records = list(_infer_records(args.input_path))

    if args.output:
        if args.format == "json":
            write_links_json(records, args.output)
        else:
            write_links_tsv(records, args.output)
        return 0

    if args.format == "json":
        print(json.dumps([record.to_dict() for record in records], indent=2))
    else:
        for record in records:
            print(record.as_tsv_row())
    return 0


__all__ = [
    "LinkRecord",
    "extract_links_from_eml",
    "extract_links_from_html",
    "read_html_from_eml",
    "run_cli",
    "write_links_json",
    "write_links_tsv",
]
