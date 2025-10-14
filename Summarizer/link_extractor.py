"""Utilities for extracting article links and metadata from Google Alert emails."""
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

SAMPLES_DIR = Path(__file__).parent / "Samples"
DEFAULT_EML = SAMPLES_DIR / "google-alert-sample-2025-10-06.eml"
DEFAULT_HTML = SAMPLES_DIR / "google-alert-sample-2025-10-06.html"
DEFAULT_LINKS_TSV = SAMPLES_DIR / "google-alert-sample-2025-10-06-links.tsv"
DEFAULT_LINKS_JSON = SAMPLES_DIR / "google-alert-sample-2025-10-06-links.json"


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
    """Extract article titles, URLs, and metadata from the alert HTML body."""
    soup = BeautifulSoup(html, "html.parser")
    records: List[LinkRecord] = []
    seen_urls: set[str] = set()

    for anchor in soup.select('a[href]'):
        href = anchor.get("href")
        if not href:
            continue

        parsed = urlparse(href)
        if parsed.netloc != "www.google.com" or parsed.path != "/url":
            # Skip feedback links and other chrome.
            continue

        params = parse_qs(parsed.query)
        target = params.get("url") or params.get("q") or params.get("u")
        if not target:
            continue
        canonical_url = target[0]
        if canonical_url in seen_urls:
            continue

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
        nargs="?",
        type=Path,
        default=DEFAULT_HTML,
        help="Path to the alert `.html` or `.eml` file (defaults to the committed sample).",
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
    "DEFAULT_EML",
    "DEFAULT_HTML",
    "DEFAULT_LINKS_TSV",
    "DEFAULT_LINKS_JSON",
]
