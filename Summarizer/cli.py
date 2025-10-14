"""Automation CLI for the Google Alert Intelligence pipeline."""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from .article_fetcher import FetchConfig, FetchError, fetch_article, clear_cache
from .config import DEFAULT_MODEL, MAX_WORKERS
from .content_cleaner import extract_content
from .digest_renderer import render_digest_html, render_digest_text
from .link_extractor import extract_links_from_eml
from .summarizer import SummarizerConfig, SummarizerError, summarize_article

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
APPLESCRIPT = PACKAGE_ROOT / "fetch-alert-source.applescript"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "article"


def capture_alert(output_path: Path, subject_filter: Optional[str] = None) -> None:
    if not APPLESCRIPT.exists():
        raise FileNotFoundError(f"AppleScript not found at {APPLESCRIPT}")

    args = ["osascript", str(APPLESCRIPT), str(output_path)]
    if subject_filter:
        args.append(subject_filter)

    result = subprocess.run(
        args,
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


def _process_single_article(
    idx: int,
    link: dict,
    articles_dir: Path,
    fetch_cfg: FetchConfig,
    sum_cfg: SummarizerConfig,
) -> Tuple[Optional[dict], Optional[dict]]:
    """Process a single article (fetch, extract, summarize).

    Returns: (summary_dict, failure_dict) - one will be None
    """
    title = link.get("title", "")
    url = link.get("url", "")
    slug = f"{idx:02d}-{slugify(title)[:40]}"
    html_path = articles_dir / f"{slug}.html"
    content_path = articles_dir / f"{slug}.content.md"
    summary_path = articles_dir / f"{slug}.summary.json"

    # Fetch article
    logging.info("[fetch] %s", url)
    try:
        html = fetch_article(url, fetch_cfg)
        html_path.write_text(html, encoding="utf-8")
    except FetchError as exc:
        logging.error("[fetch][ERROR] %s", exc)
        reason = str(exc)
        prefix = f"Failed to fetch {url}: "
        if reason.startswith(prefix):
            reason = reason[len(prefix):]
        return None, {"url": url, "reason": reason}

    # Extract content
    try:
        content_text = extract_content(html)
        if not content_text.strip():
            raise ValueError("no content extracted")
        content_path.write_text(content_text, encoding="utf-8")
    except Exception as exc:  # pragma: no cover - upstream failures
        logging.error("[clean][ERROR] %s -> %s", url, exc)
        return None, {"url": url, "reason": f"clean failed: {exc}"}

    # Summarize
    article_payload = {
        "title": title,
        "url": url,
        "publisher": link.get("publisher", ""),
        "snippet": link.get("snippet", ""),
        "content": content_text,
    }

    try:
        summary = summarize_article(article_payload, config=sum_cfg)
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        logging.info("[summarize] %s", title)
        return summary, None
    except SummarizerError as exc:
        logging.error("[summarize][ERROR] %s", exc)
        return None, {"url": url, "reason": f"summarize failed: {exc}"}


def process_articles(
    links: List[dict],
    output_dir: Path,
    fetch_cfg: FetchConfig,
    sum_cfg: SummarizerConfig,
    max_articles: int | None = None,
) -> Tuple[List[dict], List[dict]]:
    """Process articles in parallel using ThreadPoolExecutor."""
    articles_dir = output_dir / "articles"
    articles_dir.mkdir(exist_ok=True)

    # Limit articles if requested
    links_to_process = links[:max_articles] if max_articles else links

    summaries = []
    failures = []

    # Process articles in parallel (see config.MAX_WORKERS for worker count)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_idx = {
            executor.submit(_process_single_article, idx, link, articles_dir, fetch_cfg, sum_cfg): idx
            for idx, link in enumerate(links_to_process, start=1)
        }

        # Collect results as they complete
        for future in as_completed(future_to_idx):
            try:
                summary, failure = future.result()
                if summary:
                    summaries.append(summary)
                if failure:
                    failures.append(failure)
            except Exception as exc:
                # Shouldn't happen since we catch exceptions in _process_single_article
                idx = future_to_idx[future]
                link = links_to_process[idx - 1]
                logging.error("[unexpected][ERROR] Article %d failed: %s", idx, exc)
                failures.append({"url": link.get("url", "unknown"), "reason": f"unexpected error: {exc}"})

    return summaries, failures


def render_outputs(summaries: List[dict], failures: List[dict], output_dir: Path) -> None:
    if not summaries and not failures:
        logging.warning("No summaries generated; skipping digest rendering")
        return
    generated_at = datetime.now()
    html_output = render_digest_html(summaries, missing=failures, generated_at=generated_at)
    text_output = render_digest_text(summaries, missing=failures, generated_at=generated_at)
    (output_dir / "digest.html").write_text(html_output, encoding="utf-8")
    (output_dir / "digest.txt").write_text(text_output, encoding="utf-8")
    (output_dir / "summaries.json").write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Google Alert Intelligence pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Fetch latest alert and generate digest")
    run_parser.add_argument("--output-dir", required=True, help="Directory to write artifacts")
    run_parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name (default: granite4:tiny-h)")
    run_parser.add_argument("--max-articles", type=int, help="Optional cap on number of articles processed")
    run_parser.add_argument(
        "--subject-filter",
        help="Optional subject filter to match inbox messages (e.g., 'Google Alert - Medication reminder')",
    )
    run_parser.add_argument(
        "--email-digest",
        action="append",
        help="Email recipient for the plaintext digest (may be repeated)",
    )
    run_parser.add_argument(
        "--email-sender",
        help="Optional sender address when emailing the digest (defaults to first recipient unless ALERT_EMAIL_SENDER is set)",
    )

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
        force=True,
    )

    logging.info("Output directory: %s", output_dir)

    clear_cache()

    alert_eml = output_dir / "alert.eml"
    # Skip capture if alert.eml already exists (e.g., from Mail rule)
    if not alert_eml.exists():
        capture_alert(alert_eml, subject_filter=args.subject_filter)
    else:
        logging.info("Using existing alert.eml from Mail rule")

    logging.info("Extracting link metadata")
    links = load_links(alert_eml)
    link_tsv = output_dir / "alert.tsv"
    write_link_tsv(links, link_tsv)

    fetch_cfg = FetchConfig()
    sum_cfg = SummarizerConfig(model=args.model)

    summaries, failures = process_articles(links, output_dir, fetch_cfg, sum_cfg, max_articles=args.max_articles)
    render_outputs(summaries, failures, output_dir)

    recipients: List[str] = []
    if args.email_digest:
        recipients.extend(args.email_digest)

    env_recipients = os.environ.get("ALERT_DIGEST_EMAIL")
    if env_recipients:
        for token in env_recipients.replace(";", ",").split(","):
            address = token.strip()
            if address:
                recipients.append(address)

    if recipients:
        sender_address: Optional[str] = None
        if args.email_sender:
            sender_address = args.email_sender.strip() or None
        if sender_address is None:
            env_sender = os.environ.get("ALERT_EMAIL_SENDER")
            if env_sender:
                sender_address = env_sender.strip() or None

        send_digest_email(output_dir, recipients, sender_address)

    if failures:
        for failure in failures:
            logging.warning("[missing] %s — %s", failure.get("url", "unknown"), failure.get("reason", "unknown"))

    logging.info("Run complete. Summaries generated: %s", len(summaries))
    return output_dir


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.command == "run":
        run_pipeline(args)
        return 0
    return 1


def send_digest_email(output_dir: Path, recipients: List[str], sender: Optional[str]) -> None:
    """Create MIME .eml file with HTML digest for Mail rule automation.

    The Mail rule AppleScript will open this .eml file, copy rendered HTML,
    and paste into a compose window for sending.

    Args:
        output_dir: Directory containing digest.html
        recipients: Non-empty list of email addresses (at least one required)
        sender: Optional sender address

    Raises:
        ValueError: If recipients list is empty
    """
    if not recipients:
        raise ValueError("Email digest requires at least one recipient via --email-digest or ALERT_DIGEST_EMAIL")

    import email
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    html_path = output_dir / "digest.html"
    if not html_path.exists():
        logging.warning("Digest HTML not found; skipping")
        return

    html_content = html_path.read_text(encoding="utf-8")

    # Use first recipient for To: field (Mail rule will handle actual sending)
    recipient = recipients[0]

    # Create MIME multipart message with HTML
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Google Alert Intelligence — {datetime.now().strftime('%B %d, %Y')}"
    msg['From'] = sender if sender else recipient
    msg['To'] = recipient

    # Attach HTML part
    html_part = MIMEText(html_content, 'html')
    msg.attach(html_part)

    # Save as .eml file
    eml_path = output_dir / "digest.eml"
    eml_path.write_text(msg.as_string(), encoding="utf-8")

    logging.info("[digest] Created MIME email: %s (%d bytes)", eml_path, eml_path.stat().st_size)




if __name__ == "__main__":
    raise SystemExit(main())
