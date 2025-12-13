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
from .config import DEFAULT_MODEL, DIGEST_SUBJECT_TEMPLATE, LMSTUDIO_BASE_URL, LMSTUDIO_MODEL, MAX_WORKERS, OLLAMA_ENABLED
from .content_cleaner import extract_content, strip_cruft
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


def extract_email_headers(eml_path: Path) -> Tuple[str, str]:
    """Extract From address and Subject from email file.

    Args:
        eml_path: Path to .eml file

    Returns:
        Tuple of (from_address, subject) - empty strings if parsing fails
    """
    from email.header import decode_header

    try:
        with open(eml_path, 'r', encoding='utf-8') as f:
            msg = email.message_from_file(f)

        from_addr = msg.get('From', '')
        subject = msg.get('Subject', '')

        # Decode MIME-encoded subject (handles =?UTF-8?Q?...?= format)
        if subject:
            decoded_parts = decode_header(subject)
            subject = ''.join(
                part.decode(encoding or 'utf-8') if isinstance(part, bytes) else part
                for part, encoding in decoded_parts
            )

        return from_addr, subject
    except Exception as exc:
        logging.warning("[headers] Failed to extract headers from %s: %s", eml_path, exc)
        return '', ''


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
    _, subject = extract_email_headers(eml_path)
    if not subject:
        return ''

    # Extract topic after "Google Alert - "
    if 'Google Alert - ' in subject:
        topic = subject.split('Google Alert - ', 1)[1]
        # Strip Unicode curly quotes (U+201C, U+201D) and regular quotes
        topic = topic.strip('\u201c\u201d"')
        return topic

    return ''


def _is_extraction_failure(content: str) -> Tuple[bool, str]:
    """Check if extracted content appears to be UI elements or references-only.

    Args:
        content: Extracted markdown content

    Returns:
        Tuple of (is_failure, reason). If is_failure is True, reason contains
        description of what failed.
    """
    from .quality_checks import check_content_quality
    result = check_content_quality(content)
    return result.is_failure, result.reason


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
            content_text = extract_content(content, url=url)
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

    # Apply cruft removal to both HTML and Markdown paths
    content_text = strip_cruft(content_text)

    content_path.write_text(content_text, encoding="utf-8")

    # Check if extraction failed and needs fallback retry
    word_count = len(content_text.split())
    is_failure, failure_reason = _is_extraction_failure(content_text)

    # Determine if we should retry with Markdown fallback
    # Both low word count and quality failures indicate readability extraction failed
    should_retry = False
    retry_reason = None

    if word_count < 100:
        should_retry = True
        retry_reason = f"insufficient content ({word_count} words)"
    elif is_failure:
        should_retry = True
        retry_reason = failure_reason

    # Attempt fallback if HTML extraction failed
    if should_retry and outcome.format == "html":
        logging.warning("[clean][RETRY] %s -> %s, trying markdown fallback", url, retry_reason)
        try:
            from .article_fetcher import _fetch_markdown_fallback
            fallback_outcome = _fetch_markdown_fallback(url, allow_cache=False)
            content_text = strip_cruft(fallback_outcome.content)

            # Update tracking
            with counter_lock:
                strategy_counter[fallback_outcome.strategy] += 1

            # Write fallback content
            fallback_md_path.write_text(fallback_outcome.content, encoding="utf-8")
            content_path.write_text(content_text, encoding="utf-8")

            logging.info(
                "[fetch][RETRY][strategy=%s][format=%s][duration=%.2fs] %s",
                fallback_outcome.strategy,
                fallback_outcome.format,
                fallback_outcome.duration,
                url,
            )

            # Re-check after fallback
            word_count = len(content_text.split())
            is_failure, failure_reason = _is_extraction_failure(content_text)

        except FetchError as exc:
            logging.error("[clean][ERROR] %s -> %s (fallback failed: %s)", url, retry_reason, exc)
            return None, {"url": url, "reason": retry_reason}

    # Final validation (after potential retry)
    suffix = " (after fallback)" if should_retry and outcome.format == "html" else ""

    if word_count < 100:
        logging.error("[clean][ERROR] %s -> insufficient content%s (%d words)", url, suffix, word_count)
        return None, {"url": url, "reason": f"only {word_count} words extracted{suffix}"}

    if is_failure:
        logging.error("[clean][ERROR] %s -> %s%s", url, failure_reason, suffix)
        return None, {"url": url, "reason": failure_reason}

    if word_count < 200:
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


def write_status_log(
    from_addr: str,
    subject: str,
    links_count: int,
    fetched_count: int,
    summaries_count: int,
    digest_created: bool,
    smtp_sent: bool,
    status: str,
    error_msg: str = "",
    failures: Optional[List[dict]] = None
) -> None:
    """Append one line to runs/summarizer-status.log with run metrics.

    Args:
        from_addr: Email From address (extracted from alert.eml)
        subject: Email subject (extracted from alert.eml)
        links_count: Number of article links extracted
        fetched_count: Number of articles successfully fetched
        summaries_count: Number of summaries generated
        digest_created: Whether digest files were created
        smtp_sent: Whether SMTP send succeeded
        status: Status string (SUCCESS or FAILED - reason)
        error_msg: Optional error message to append to FAILED status
        failures: Optional list of failure dicts with 'url' and 'reason' keys
    """
    status_log = REPO_ROOT / "runs" / "summarizer-status.log"
    status_log.parent.mkdir(parents=True, exist_ok=True)

    # Truncate long subjects for readability
    display_subject = subject if len(subject) <= 40 else subject[:37] + "..."

    # Build status string
    status_str = status
    if error_msg and "FAILED" in status:
        status_str = f"{status} - {error_msg}"

    # Format log entry
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    digest_str = "Yes" if digest_created else "No"
    smtp_str = "Yes" if smtp_sent else "No"
    failed_count = len(failures) if failures else 0

    log_entry = (
        f'{timestamp} | From: {from_addr} | Subject: "{display_subject}" | '
        f'Links: {links_count} | Fetched: {fetched_count} | Summaries: {summaries_count} | Failed: {failed_count} | '
        f'Digest: {digest_str} | SMTP: {smtp_str} | Status: {status_str}\n'
    )

    with open(status_log, "a", encoding="utf-8") as f:
        f.write(log_entry)

    logging.info("[status-log] Entry written to %s", status_log)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Google Alert Intelligence pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Fetch latest alert and generate digest")
    run_parser.add_argument("--output-dir", required=True, help="Directory to write artifacts")
    run_parser.add_argument("--model", help="Override LLM model name (uses LMSTUDIO_MODEL or OLLAMA_MODEL from .env by default)")
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

    # Evaluation subcommand
    eval_parser = subparsers.add_parser("eval", help="Evaluate LLM models on summarization task")
    eval_parser.add_argument(
        "--models",
        default="all",
        help="Comma-separated list of model IDs to evaluate, or 'all' to evaluate all available models (default: all)",
    )
    eval_parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of runs per article for consistency testing (default: 3)",
    )
    eval_parser.add_argument(
        "--output",
        default="eval_report.md",
        help="Output path for evaluation report (default: eval_report.md)",
    )
    eval_parser.add_argument(
        "--articles-dir",
        help="Directory containing article content files (defaults to most recent runs/alert-* directory)",
    )

    return parser.parse_args(argv)


def run_pipeline(args: argparse.Namespace) -> Path:
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    log_file = output_dir / "workflow.log"
    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(asctime)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )

    logging.info("Output directory: %s", output_dir)

    # Initialize metrics tracking
    from_addr = ""
    subject = ""
    links_count = 0
    fetched_count = 0
    summaries_count = 0
    failures: List[dict] = []
    digest_created = False
    smtp_sent = False
    status = "SUCCESS"
    error_msg = ""

    try:
        clear_cache()

        alert_eml = output_dir / "alert.eml"
        # Skip capture if alert.eml already exists (e.g., from Mail rule)
        if not alert_eml.exists():
            capture_alert(alert_eml, subject_filter=args.subject_filter)
        else:
            logging.info("Using existing alert.eml from Mail rule")

        # Extract email headers for status logging
        from_addr, subject = extract_email_headers(alert_eml)

        logging.info("Extracting link metadata")
        links = load_links(alert_eml)
        links_count = len(links)
        link_tsv = output_dir / "alert.tsv"
        write_link_tsv(links, link_tsv)

        fetch_cfg = FetchConfig()
        sum_cfg = SummarizerConfig(model=args.model)

        # Pre-flight check: Ensure LM Studio model is ready before fetching articles
        if LMSTUDIO_BASE_URL and LMSTUDIO_MODEL:
            from .summarizer import _ensure_correct_model_loaded
            logging.info("[preflight] Verifying LM Studio model is loaded...")
            success, message = _ensure_correct_model_loaded(LMSTUDIO_BASE_URL, sum_cfg.model or LMSTUDIO_MODEL)
            if not success:
                logging.error("[preflight] Model setup failed: %s", message)
                if not OLLAMA_ENABLED:
                    raise RuntimeError(f"Cannot proceed: {message}")
                logging.info("[preflight] Will attempt Ollama fallback")
            else:
                logging.info("[preflight] %s", message)

        summaries, failures = process_articles(links, output_dir, fetch_cfg, sum_cfg, max_articles=args.max_articles)
        summaries_count = len(summaries)
        fetched_count = summaries_count + len(failures)  # Total articles that were attempted

        # Check for failure condition: 0 summaries generated
        if summaries_count == 0:
            separator = "=" * 80
            logging.warning(
                f"\n{separator}\n"
                f"WARNING: NO SUMMARIES GENERATED\n"
                f"{separator}\n"
                f"From: {from_addr}\n"
                f"Subject: {subject}\n"
                f"Links extracted: {links_count}\n"
                f"Articles fetched: {fetched_count}\n"
                f"Summaries generated: 0\n"
                f"\n"
                f"This is a FAILURE condition. Pipeline completed but produced no output.\n"
                f"{separator}"
            )
            status = "FAILED"
            if links_count == 0:
                error_msg = "No article links found"
            else:
                error_msg = "No summaries generated"

        # Extract topic from alert email if not provided via --topic flag
        topic = args.topic
        if not topic:
            topic = extract_topic_from_alert_eml(alert_eml)
            if topic:
                logging.info("[topic] Extracted from alert email: %s", topic)

        render_outputs(summaries, failures, output_dir, topic=topic)
        if summaries or failures:
            digest_created = True

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
            send_digest_email(output_dir, recipients, sender_address, topic=topic, article_count=summaries_count)

            # If --smtp-send flag is set, send via SMTP instead of UI automation
            if args.smtp_send:
                eml_path = output_dir / "digest.eml"
                if eml_path.exists():
                    recipient = recipients[0]
                    try:
                        send_digest_via_smtp(eml_path, recipient)
                        logging.info("[smtp] Digest sent to %s", recipient)
                        smtp_sent = True
                    except (ValueError, FileNotFoundError, smtplib.SMTPException, ConnectionError) as exc:
                        logging.error("[smtp][ERROR] Failed to send digest: %s", exc)
                        status = "FAILED"
                        error_msg = f"SMTP send failed: {exc}"
                        raise
                else:
                    logging.warning("[smtp] No digest generated; skipping SMTP send")

        if failures:
            for failure in failures:
                logging.warning("[missing] %s — %s", failure.get("url", "unknown"), failure.get("reason", "unknown"))

        logging.info("Run complete. Summaries generated: %s", len(summaries))

    except Exception as exc:
        status = "FAILED"
        error_msg = str(exc)
        logging.error("[pipeline][ERROR] Pipeline failed: %s", exc)
        raise
    finally:
        # Always write status log, even on failure
        write_status_log(
            from_addr=from_addr,
            subject=subject,
            links_count=links_count,
            fetched_count=fetched_count,
            summaries_count=summaries_count,
            digest_created=digest_created,
            smtp_sent=smtp_sent,
            status=status,
            error_msg=error_msg,
            failures=failures,
        )

    return output_dir


def run_eval(args: argparse.Namespace) -> int:
    """Run model evaluation on gold standard articles.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 on success)
    """
    from .evals import ModelEvaluator, GOLD_ANNOTATIONS
    from .evals.report import generate_markdown_report, save_report

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(message)s",
        handlers=[logging.StreamHandler()],
        force=True,
    )

    # Initialize evaluator
    try:
        evaluator = ModelEvaluator()
    except ValueError as exc:
        logging.error("Failed to initialize evaluator: %s", exc)
        return 1

    # Determine which models to evaluate
    if args.models == "all":
        models = evaluator.get_available_models()
        if not models:
            logging.error("No models available in LM Studio")
            return 1
        logging.info("Found %d models to evaluate", len(models))
    else:
        models = [m.strip() for m in args.models.split(",")]
        logging.info("Evaluating %d specified models", len(models))

    # Load test articles
    from .evals.load_articles import load_articles_from_directory, load_articles_from_runs

    if args.articles_dir:
        articles_dir = Path(args.articles_dir)
        articles = load_articles_from_directory(articles_dir)
    else:
        articles = load_articles_from_runs()

    if not articles:
        logging.error("No articles loaded for evaluation")
        return 1

    logging.info("Loaded %d articles for evaluation", len(articles))

    # Run evaluation
    results = {}
    for model in models:
        logging.info("=" * 80)
        logging.info("Evaluating model: %s", model)
        logging.info("=" * 80)

        try:
            model_results = evaluator.evaluate_model(model, articles, runs=args.runs)
            results[model] = model_results
        except Exception as exc:
            logging.error("Failed to evaluate model %s: %s", model, exc)
            import traceback
            traceback.print_exc()

    if not results:
        logging.error("No evaluation results generated")
        return 1

    # Generate and save report
    report = generate_markdown_report(results)
    save_report(results, args.output)

    # Print summary to console
    print("\n" + "=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)
    print(f"\nReport saved to: {args.output}")
    print(f"\nEvaluated {len(results)} models on {len(articles)} articles")
    print("\nTop 3 Models by Accuracy:")

    sorted_models = sorted(
        results.items(),
        key=lambda x: x[1].avg_accuracy,
        reverse=True,
    )[:3]

    for rank, (model, model_results) in enumerate(sorted_models, 1):
        print(f"  {rank}. {model}: {model_results.avg_accuracy:.1%}")

    return 0


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.command == "run":
        run_pipeline(args)
        return 0
    elif args.command == "eval":
        return run_eval(args)
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


def send_digest_email(output_dir: Path, recipients: List[str], sender: Optional[str], topic: Optional[str] = None, article_count: int = 0) -> None:
    """Create MIME .eml file with HTML digest for Mail rule automation.

    The Mail rule AppleScript will open this .eml file, copy rendered HTML,
    and paste into a compose window for sending.

    Args:
        output_dir: Directory containing digest.html
        recipients: Non-empty list of email addresses (at least one required)
        sender: Optional sender address
        topic: Optional alert topic to include in subject line
        article_count: Number of articles in the digest

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
    # Format subject using template from config
    subject = DIGEST_SUBJECT_TEMPLATE.format(
        topic=topic or "Alert",
        count=article_count,
        date=datetime.now().strftime('%B %d, %Y')
    )
    msg['Subject'] = subject
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
