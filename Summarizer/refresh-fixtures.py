#!/usr/bin/env python3
"""Regenerate Summarizer fixtures from a raw Google Alert .eml export."""
from __future__ import annotations

import argparse
from pathlib import Path

from link_extractor import (
    DEFAULT_EML,
    DEFAULT_HTML,
    DEFAULT_LINKS_JSON,
    DEFAULT_LINKS_TSV,
    extract_links_from_html,
    read_html_from_eml,
    write_links_json,
    write_links_tsv,
)


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
        default=DEFAULT_LINKS_TSV,
        help="Where to write the expected link/title pairs (TSV).",
    )
    parser.add_argument(
        "--links-json",
        type=Path,
        default=DEFAULT_LINKS_JSON,
        help="Where to write the structured JSON output.",
    )
    args = parser.parse_args()

    html = read_html_from_eml(args.eml)
    args.html.write_text(html, encoding="utf-8")

    records = extract_links_from_html(html)
    write_links_tsv(records, args.links)
    write_links_json(records, args.links_json)

    print(f"Wrote HTML to {args.html}")
    print(f"Wrote link TSV to {args.links}")
    print(f"Wrote link JSON to {args.links_json}")


if __name__ == "__main__":
    main()
