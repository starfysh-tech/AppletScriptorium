"""Automation CLI for the Google Alert Intelligence pipeline."""
from __future__ import annotations

import argparse
import csv
import email
import json
import logging
import os
import re
import smtplib
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Iterable, List, Optional, Tuple

from dotenv import load_dotenv

# CRITICAL: Load .env BEFORE importing config module
# config.py reads environment variables during import, so .env must be loaded first
PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
load_dotenv(REPO_ROOT / '.env', override=True)

from .article_fetcher import (
    FetchConfig,
    FetchError,
    clear_cache,
    fetch_article,
    get_last_fetch_outcome,
)
from .config import DEFAULT_MODEL, MAX_WORKERS
from .content_cleaner import extract_content
from .digest_renderer import render_digest_html, render_digest_text
from .link_extractor import extract_links_from_eml
from .markdown_cleanup import validate_markdown_content
from .summarizer import SummarizerConfig, SummarizerError, summarize_article

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


def extract_topic_from_alert_eml(eml_path: Path) -> str:
    """Extract Google Alert topic from email subject using proper MIME decoding.

    Handles RFC 2047 MIME-encoded subjects (e.g., =?UTF-8?Q?...?=) and strips
    Unicode curly quotes that commonly appear in Google Alert subjects.

    Args:
        eml_path: Path to .eml file

    Returns:
        Extracted topic string, or empty string if not found/parseable

    Example:
        Subject: =?UTF-8?Q?Google_Alert_=2D_=E2=80=9CPatient_reported_outcome=E2=80=9D?=
        Returns: "Patient reported outcome"
    """
    from email.header import decode_header

    try:
        with open(eml_path, 'r', encoding='utf-8') as f:
            msg = email.message_from_file(f)

        subject = msg.get('Subject', '')
        if not subject:
            return ''

        # Decode MIME-encoded subject (handles =?UTF-8?Q?...?= format)
        decoded_parts = decode_header(subject)
        subject_text = ''.join(
            part.decode(encoding or 'utf-8') if isinstance(part, bytes) else part
            for part, encoding in decoded_parts
        )

        # Extract topic after "Google Alert - "
        if 'Google Alert - ' in subject_text:
            topic = subject_text.split('Google Alert - ', 1)[1]
            # Strip Unicode curly quotes (U+201C, U+201D) and regular quotes
            topic = topic.strip('\u201c\u201d"')
            return topic

        return ''
    except Exception as exc:
        logging.warning("[topic] Failed to extract topic from %s: %s", eml_path, exc)
        return ''


def _fetch_and_extract_article(
    idx: int,
    link: dict,
    articles_dir: Path,
    fetch_cfg: FetchConfig,
    strategy_counter: Counter,
    counter_lock: Lock,
) -> Tuple[Optional[dict], Optional[dict]]:
    """Fetch and extract content from a single article.

    This function runs in parallel across multiple workers.

    Returns: (article_data, failure_dict) - one will be None
    article_data contains: title, url, publisher, snippet, content, summary_path
    """
    title = link.get("title", "")
    url = link.get("url", "")
    slug = f"{idx:02d}-{slugify(title)[:40]}"
    html_path = articles_dir / f"{slug}.html"
    fallback_md_path = articles_dir / f"{slug}.fallback.md"
    content_path = articles_dir / f"{slug}.content.md"
    summary_path = articles_dir / f"{slug}.summary.json"

    # Fetch article
    logging.info("[fetch] %s", url)
    try:
        content = fetch_article(url, fetch_cfg)
    except FetchError as exc:
        logging.error("[fetch][ERROR] %s", exc)
        reason = str(exc)
        prefix = f"Failed to fetch {url}: "
        if reason.startswith(prefix):
            reason = reason[len(prefix):]
        return None, {"url": url, "reason": reason}

    outcome = get_last_fetch_outcome()
    if outcome is None:
        logging.error("[fetch][ERROR] %s", "missing fetch metadata")
        return None, {"url": url, "reason": "internal error: missing fetch metadata"}

    removed_count = len(outcome.removed_sections)
    logging.info(
        "[fetch][strategy=%s][format=%s][duration=%.2fs][removed=%d] %s",
        outcome.strategy,
        outcome.format,
        outcome.duration,
        removed_count,
        url,
    )

    with counter_lock:
        strategy_counter[outcome.strategy] += 1

    if outcome.format == "html":
        fallback_md_path.unlink(missing_ok=True)
        html_path.write_text(content, encoding="utf-8")
        try:
            content_text = extract_content(content)
            if not content_text.strip():
                raise ValueError("no content extracted")
        except Exception as exc:  # pragma: no cover - upstream failures
            logging.error("[clean][ERROR] %s -> %s", url, exc)
            return None, {"url": url, "reason": f"clean failed: {exc}"}
    else:
        html_path.unlink(missing_ok=True)
        fallback_md_path.write_text(content, encoding="utf-8")
        warnings = validate_markdown_content(content)
        if warnings:
            logging.warning("[validate] %s: %s", url, ", ".join(warnings))
        content_text = content
        if not content_text.strip():
            logging.error("[clean][ERROR] %s -> empty markdown content", url)
            return None, {"url": url, "reason": "clean failed: empty markdown"}

    content_path.write_text(content_text, encoding="utf-8")

    # Validate extracted content length to catch extraction failures
    word_count = len(content_text.split())
    if word_count < 100:
        logging.error("[clean][ERROR] %s -> insufficient content (%d words)", url, word_count)
        return None, {"url": url, "reason": f"only {word_count} words extracted (likely extraction failure)"}
    elif word_count < 200:
        logging.warning("[clean][WARN] %s -> short content (%d words), summary quality may be poor", url, word_count)

    # Return article data for Phase 2 summarization
    article_data = {
        "title": title,
        "url": url,
        "publisher": link.get("publisher", ""),
        "snippet": link.get("snippet", ""),
        "content": content_text,
        "summary_path": summary_path,
    }

    return article_data, None


def _summarize_article(
    article_data: dict,
    sum_cfg: SummarizerConfig,
) -> Tuple[Optional[dict], Optional[dict]]:
    """Summarize a single article using Ollama.

    This function runs sequentially to prevent Ollama daemon overload.

    Returns: (summary_dict, failure_dict) - one will be None
    """
    title = article_data["title"]
    url = article_data["url"]
    summary_path = article_data["summary_path"]

    article_payload = {
        "title": title,
        "url": url,
        "publisher": article_data["publisher"],
        "snippet": article_data["snippet"],
        "content": article_data["content"],
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
    """Process articles in two phases to prevent Ollama daemon overload.

    Phase 1: Parallel fetch and content extraction (I/O-bound, uses MAX_WORKERS)
    Phase 2: Sequential summarization (CPU-bound, prevents Ollama deadlock)
    """
    articles_dir = output_dir / "articles"
    articles_dir.mkdir(exist_ok=True)

    # Limit articles if requested
    links_to_process = links[:max_articles] if max_articles else links

    summaries: List[dict] = []
    failures: List[dict] = []
    strategy_counter: Counter = Counter()
    counter_lock = Lock()

    # PHASE 1: Parallel fetch and content extraction
    article_data_list: List[dict] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all fetch tasks
        future_to_idx = {
            executor.submit(
                _fetch_and_extract_article,
                idx,
                link,
                articles_dir,
                fetch_cfg,
                strategy_counter,
                counter_lock,
            ): idx
            for idx, link in enumerate(links_to_process, start=1)
        }

        # Collect fetch results as they complete
        for future in as_completed(future_to_idx):
            try:
                article_data, failure = future.result()
                if article_data:
                    article_data_list.append(article_data)
                if failure:
                    failures.append(failure)
            except Exception as exc:
                # Shouldn't happen since we catch exceptions in _fetch_and_extract_article
                idx = future_to_idx[future]
                link = links_to_process[idx - 1]
                logging.error("[unexpected][ERROR] Article %d failed: %s", idx, exc)
                failures.append({"url": link.get("url", "unknown"), "reason": f"unexpected error: {exc}"})

    if strategy_counter:
        summary_parts = ", ".join(f"{key}={count}" for key, count in sorted(strategy_counter.items()))
        logging.info("Fetch summary: %s", summary_parts)

    # PHASE 2: Sequential summarization (prevent Ollama daemon overload)
    for article_data in article_data_list:
        try:
            summary, failure = _summarize_article(article_data, sum_cfg)
            if summary:
                summaries.append(summary)
            if failure:
                failures.append(failure)
        except Exception as exc:
            # Shouldn't happen since we catch exceptions in _summarize_article
            url = article_data.get("url", "unknown")
            logging.error("[unexpected][ERROR] Summarization failed: %s", exc)
            failures.append({"url": url, "reason": f"unexpected error: {exc}"})

    return summaries, failures


def render_outputs(summaries: List[dict], failures: List[dict], output_dir: Path, topic: Optional[str] = None) -> None:
    if not summaries and not failures:
        logging.warning("No summaries generated; skipping digest rendering")
        return
    generated_at = datetime.now()
    html_output = render_digest_html(summaries, missing=failures, generated_at=generated_at, topic=topic)
    text_output = render_digest_text(summaries, missing=failures, generated_at=generated_at, topic=topic)
    (output_dir / "digest.html").write_text(html_output, encoding="utf-8")
    (output_dir / "digest.txt").write_text(text_output, encoding="utf-8")
    (output_dir / "summaries.json").write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Google Alert Intelligence pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Fetch latest alert and generate digest")
    run_parser.add_argument("--output-dir", required=True, help="Directory to write artifacts")
    run_parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name (default: qwen3:latest)")
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
    run_parser.add_argument(
        "--smtp-send",
        action="store_true",
        help="Send digest via SMTP instead of creating .eml file for UI automation (requires SMTP_USERNAME and SMTP_PASSWORD environment variables)",
    )
    run_parser.add_argument(
        "--topic",
        help="Alert topic to include in email subject (e.g., 'Patient reported outcomes')",
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

    # Extract topic from alert email if not provided via --topic flag
    topic = args.topic
    if not topic:
        topic = extract_topic_from_alert_eml(alert_eml)
        if topic:
            logging.info("[topic] Extracted from alert email: %s", topic)

    render_outputs(summaries, failures, output_dir, topic=topic)

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

        # Create .eml file (may not be created if no summaries generated)
        send_digest_email(output_dir, recipients, sender_address, topic=topic)

        # If --smtp-send flag is set, send via SMTP instead of UI automation
        if args.smtp_send:
            eml_path = output_dir / "digest.eml"
            if eml_path.exists():
                recipient = recipients[0]
                try:
                    send_digest_via_smtp(eml_path, recipient)
                    logging.info("[smtp] Digest sent to %s", recipient)
                except (ValueError, FileNotFoundError, smtplib.SMTPException, ConnectionError) as exc:
                    logging.error("[smtp][ERROR] Failed to send digest: %s", exc)
                    raise
            else:
                logging.warning("[smtp] No digest generated; skipping SMTP send")

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


def send_digest_via_smtp(eml_path: Path, recipient: str) -> None:
    """Send digest email via SMTP instead of UI automation.

    Loads SMTP credentials from environment variables and sends the
    existing digest.eml file directly via SMTP protocol.

    Args:
        eml_path: Path to digest.eml file
        recipient: Email recipient address

    Environment Variables:
        SMTP_USERNAME: SMTP username (e.g., user@gmail.com)
        SMTP_PASSWORD: SMTP password (use app password for Gmail)
        SMTP_HOST: SMTP server (default: smtp.gmail.com)
        SMTP_PORT: SMTP port (default: 587)

    Raises:
        FileNotFoundError: If .eml file doesn't exist
        ValueError: If required environment variables are missing
        smtplib.SMTPException: On SMTP errors (connection, auth, send)
        ConnectionError: On network connection failures
    """
    # Load SMTP configuration from environment
    smtp_user = os.environ.get("SMTP_USERNAME")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = os.environ.get("SMTP_PORT", "587")

    if not smtp_user or not smtp_password:
        raise ValueError(
            "SMTP credentials missing. Set SMTP_USERNAME and SMTP_PASSWORD environment variables in .env file.\n"
            "For Gmail, generate app password at: https://myaccount.google.com/apppasswords"
        )

    # Validate port is numeric
    try:
        smtp_port = str(int(smtp_port))
    except ValueError:
        raise ValueError(f"SMTP_PORT must be numeric, got: {smtp_port}")

    # Load .eml file
    if not eml_path.exists():
        raise FileNotFoundError(f"EML file not found: {eml_path}")

    logging.info("[smtp] Reading .eml file: %s", eml_path)

    with open(eml_path, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        msg = email.message_from_string(content)
    except Exception as exc:
        raise ValueError(f"Failed to parse .eml file: {exc}")

    from_addr = msg.get("From", smtp_user)
    to_addr = recipient

    logging.info("[smtp] Connecting to %s:%s", smtp_host, smtp_port)

    try:
        with smtplib.SMTP(smtp_host, int(smtp_port), timeout=30) as server:
            server.set_debuglevel(0)

            logging.info("[smtp] Starting TLS encryption")
            server.starttls()

            logging.info("[smtp] Authenticating as: %s", smtp_user)
            try:
                server.login(smtp_user, smtp_password)
            except smtplib.SMTPAuthenticationError as exc:
                error_msg = f"Authentication failed. Check GMAIL_APP_PASSWORD (use app password, not account password)"
                if exc.smtp_error:
                    error_msg += f": {exc.smtp_error.decode()}"
                raise smtplib.SMTPAuthenticationError(exc.smtp_code, error_msg)

            logging.info("[smtp] Sending email to: %s", to_addr)
            server.sendmail(from_addr, [to_addr], msg.as_string())

            logging.info("[smtp] Email sent successfully!")

    except smtplib.SMTPConnectError as exc:
        raise ConnectionError(f"Failed to connect to SMTP server: {exc}")
    except smtplib.SMTPServerDisconnected as exc:
        raise ConnectionError(f"SMTP server disconnected unexpectedly: {exc}")
    except smtplib.SMTPException as exc:
        raise smtplib.SMTPException(f"SMTP error: {exc}")


def send_digest_email(output_dir: Path, recipients: List[str], sender: Optional[str], topic: Optional[str] = None) -> None:
    """Create MIME .eml file with HTML digest for Mail rule automation.

    The Mail rule AppleScript will open this .eml file, copy rendered HTML,
    and paste into a compose window for sending.

    Args:
        output_dir: Directory containing digest.html
        recipients: Non-empty list of email addresses (at least one required)
        sender: Optional sender address
        topic: Optional alert topic to include in subject line

    Raises:
        ValueError: If recipients list is empty
    """
    if not recipients:
        raise ValueError("Email digest requires at least one recipient via --email-digest or ALERT_DIGEST_EMAIL")

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
    topic_text = f": {topic}" if topic else ""
    msg['Subject'] = f"Google Alert Intelligence{topic_text} — {datetime.now().strftime('%B %d, %Y')}"
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
