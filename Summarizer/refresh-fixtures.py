#!/usr/bin/env python3
"""Regenerate Summarizer fixtures from a raw Google Alert .eml export."""
from __future__ import annotations

import argparse
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Iterable, Tuple
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup


SAMPLES_DIR = Path(__file__).parent / "Samples"
DEFAULT_EML = SAMPLES_DIR / "google-alert-patient-reported-outcome-2025-10-06.eml"
DEFAULT_HTML = SAMPLES_DIR / "google-alert-patient-reported-outcome-2025-10-06.html"
DEFAULT_LINKS = SAMPLES_DIR / "google-alert-patient-reported-outcome-2025-10-06-links.tsv"


def extract_html(eml_path: Path) -> str:
    with eml_path.open("rb") as handle:
        message = BytesParser(policy=policy.default).parse(handle)

    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/html":
                return part.get_content()
    elif message.get_content_type() == "text/html":
        return message.get_content()

    raise ValueError(f"No HTML part found in {eml_path}")


def parse_links(html: str) -> Iterable[Tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[Tuple[str, str]] = set()

    for anchor in soup.select("a[href]"):
        href = anchor["href"]
        if "www.google.com/url" not in href:
            continue

        title = anchor.get_text(" ", strip=True)
        if not title:
            continue

        parsed = urlparse(href)
        params = parse_qs(parsed.query)
        target = params.get("url") or params.get("q") or params.get("u")
        url = target[0] if target else href
        record = (title, url)

        if record in seen:
            continue
        seen.add(record)
        yield record


def write_links(records: Iterable[Tuple[str, str]], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as handle:
        for title, url in records:
            handle.write(f"{title}\t{url}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "eml",
        nargs="?",
        type=Path,
        default=DEFAULT_EML,
        help="Path to the Google Alert .eml file (defaults to the committed fixture).",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=DEFAULT_HTML,
        help="Where to write the decoded HTML body.",
    )
    parser.add_argument(
        "--links",
        type=Path,
        default=DEFAULT_LINKS,
        help="Where to write the expected link/title pairs (TSV).",
    )
    args = parser.parse_args()

    html = extract_html(args.eml)
    args.html.write_text(html, encoding="utf-8")
    write_links(parse_links(html), args.links)

    print(f"Wrote HTML to {args.html}")
    print(f"Wrote link list to {args.links}")


if __name__ == "__main__":
    main()
