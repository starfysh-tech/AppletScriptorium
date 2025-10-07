"""Automation CLI for the PRO Alert Summarizer pipeline."""
from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from article_fetcher import FetchConfig, FetchError, fetch_article, clear_cache
from content_cleaner import extract_content
from digest_renderer import render_digest_html, render_digest_text
from link_extractor import DEFAULT_EML, extract_links_from_eml
from summarizer import SummarizerConfig, SummarizerError, summarize_article

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
APPLESCRIPT = PACKAGE_ROOT / "fetch-alert-source.applescript"
DEFAULT_MODEL = "granite4:tiny-h"
SUMMARY_LIMIT = 3


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "article"


def capture_alert(output_path: Path) -> None:
    if not APPLESCRIPT.exists():
        raise FileNotFoundError(f"AppleScript not found at {APPLESCRIPT}")
    result = subprocess.run(
        ["osascript", str(APPLESCRIPT), str(output_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    logging.info(result.stdout.strip())
    if result.returncode != 0:
        raise RuntimeError(f"osascript failed: {result.stderr.strip()}")


def load_links(eml_path: Path) -> List[dict]:
    records = extract_links_from_eml(eml_path)
    links = []
    for record in records:
        links.append({
            "title": record.title,
            "url": record.url,
            "publisher": getattr(record, "publisher", ""),
            "snippet": getattr(record, "snippet", ""),
        })
    return links


def write_link_tsv(links: Iterable[dict], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile, delimiter="\t")
        for link in links:
            writer.writerow([
                link.get("title", ""),
                link.get("url", ""),
                link.get("publisher", ""),
                link.get("snippet", ""),
            ])


def process_articles(
    links: List[dict],
    output_dir: Path,
    fetch_cfg: FetchConfig,
    sum_cfg: SummarizerConfig,
    max_articles: int | None = None,
) -> List[dict]:
    articles_dir = output_dir / "articles"
    articles_dir.mkdir(exist_ok=True)
    summaries = []

    count = 0
    for idx, link in enumerate(links, start=1):
        if max_articles is not None and count >= max_articles:
            break
        title = link.get("title", "")
        url = link.get("url", "")
        slug = f"{idx:02d}-{slugify(title)[:40]}"
        html_path = articles_dir / f"{slug}.html"
        content_path = articles_dir / f"{slug}.content.json"
        summary_path = articles_dir / f"{slug}.summary.json"

        logging.info("[fetch] %s", url)
        try:
            html = fetch_article(url, fetch_cfg)
            html_path.write_text(html, encoding="utf-8")
        except FetchError as exc:
            logging.error("[fetch][ERROR] %s", exc)
            continue

        try:
            content_blocks = extract_content(html)
            content_path.write_text(json.dumps(content_blocks, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:  # pragma: no cover - upstream failures
            logging.error("[clean][ERROR] %s -> %s", url, exc)
            continue

        article_payload = {
            "title": title,
            "url": url,
            "publisher": link.get("publisher", ""),
            "snippet": link.get("snippet", ""),
            "content": content_blocks,
        }

        try:
            summary = summarize_article(article_payload, config=sum_cfg)
            summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
            summaries.append(summary)
            logging.info("[summarize] %s", title)
            count += 1
        except SummarizerError as exc:
            logging.error("[summarize][ERROR] %s", exc)

    return summaries


def render_outputs(summaries: List[dict], output_dir: Path) -> None:
    if not summaries:
        logging.warning("No summaries generated; skipping digest rendering")
        return
    generated_at = datetime.now()
    html_output = render_digest_html(summaries, generated_at=generated_at)
    text_output = render_digest_text(summaries, generated_at=generated_at)
    (output_dir / "digest.html").write_text(html_output, encoding="utf-8")
    (output_dir / "digest.txt").write_text(text_output, encoding="utf-8")
    (output_dir / "summaries.json").write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the PRO Alert Summarizer pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Fetch latest alert and generate digest")
    run_parser.add_argument("--output-dir", required=True, help="Directory to write artifacts")
    run_parser.add_argument("--stub-manifest", help="JSON manifest for stubbed article HTML (for testing)")
    run_parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name (default: granite4:tiny-h)")
    run_parser.add_argument("--max-articles", type=int, help="Optional cap on number of articles processed")

    return parser.parse_args(argv)


def run_pipeline(args: argparse.Namespace) -> Path:
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    log_file = output_dir / "workflow.log"
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    logging.info("Output directory: %s", output_dir)

    clear_cache()

    alert_eml = output_dir / "alert.eml"
    capture_alert(alert_eml)

    logging.info("Extracting link metadata")
    links = load_links(alert_eml)
    link_tsv = output_dir / "alert.tsv"
    write_link_tsv(links, link_tsv)

    stub_manifest = Path(args.stub_manifest).expanduser().resolve() if args.stub_manifest else None
    fetch_cfg = FetchConfig(stub_manifest=stub_manifest)
    sum_cfg = SummarizerConfig(model=args.model)

    summaries = process_articles(links, output_dir, fetch_cfg, sum_cfg, max_articles=args.max_articles)
    render_outputs(summaries, output_dir)

    logging.info("Run complete. Summaries generated: %s", len(summaries))
    return output_dir


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.command == "run":
        run_pipeline(args)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
