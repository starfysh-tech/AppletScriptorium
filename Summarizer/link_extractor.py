"""Utilities for extracting article links from Google Alert emails."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

SAMPLES_DIR = Path(__file__).parent / "Samples"
DEFAULT_EML = SAMPLES_DIR / "google-alert-patient-reported-outcome-2025-10-06.eml"
DEFAULT_HTML = SAMPLES_DIR / "google-alert-patient-reported-outcome-2025-10-06.html"
DEFAULT_LINKS_TSV = SAMPLES_DIR / "google-alert-patient-reported-outcome-2025-10-06-links.tsv"


@dataclass(frozen=True)
class LinkRecord:
    """Represents a single article entry extracted from the alert."""

    title: str
    url: str

    def as_tsv_row(self) -> str:
        return f"{self.title}\t{self.url}"


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
    """Extract article titles and URLs from the alert HTML body."""
    soup = BeautifulSoup(html, "html.parser")
    records: List[LinkRecord] = []
    seen: set[Tuple[str, str]] = set()

    for anchor in soup.select("a[href]"):
        href = anchor.get("href")
        if not href:
            continue

        parsed = urlparse(href)
        if parsed.netloc != "www.google.com" or parsed.path != "/url":
            # Skip feedback links and other chrome.
            continue

        title = anchor.get_text(" ", strip=True)
        if not title:
            continue

        params = parse_qs(parsed.query)
        target = params.get("url") or params.get("q") or params.get("u")
        if not target:
            continue

        record = (title, target[0])
        if record in seen:
            continue
        seen.add(record)
        records.append(LinkRecord(title=record[0], url=record[1]))

    return records


def extract_links_from_eml(eml_path: Path) -> List[LinkRecord]:
    """Convenience wrapper to extract links directly from an `.eml` file."""
    html = read_html_from_eml(eml_path)
    return extract_links_from_html(html)


def write_links(records: Sequence[LinkRecord], output_path: Path) -> None:
    output_path.write_text("\n".join(record.as_tsv_row() for record in records) + "\n", encoding="utf-8")


def _infer_reader(path: Path) -> Iterable[LinkRecord]:
    suffix = path.suffix.lower()
    if suffix == ".eml":
        return extract_links_from_eml(path)
    if suffix in {".html", ".htm"}:
        html = path.read_text(encoding="utf-8")
        return extract_links_from_html(html)
    raise UnsupportedInputError(f"Unsupported file type for {path}")


def run_cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract link/title pairs from a Google Alert export.")
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
        help="Optional output path. Writes TSV when provided; otherwise prints to stdout.",
    )
    args = parser.parse_args(argv)

    records = list(_infer_reader(args.input_path))

    if args.output:
        write_links(records, args.output)
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
    "write_links",
    "DEFAULT_EML",
    "DEFAULT_HTML",
    "DEFAULT_LINKS_TSV",
]
