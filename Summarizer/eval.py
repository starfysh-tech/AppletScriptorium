"""Multi-model evaluation for Summarizer pipeline.

Usage examples:

    # Generate corpus and evaluate all models
    python3 -m Summarizer.eval google-alert.eml --output-dir evals/eval-001

    # Generate corpus only (for later reuse)
    python3 -m Summarizer.eval google-alert.eml --corpus-only --output-dir evals/eval-001

    # Evaluate using existing corpus
    python3 -m Summarizer.eval --corpus-dir evals/eval-001/corpus --output-dir evals/eval-002

    # Filter backends
    python3 -m Summarizer.eval google-alert.eml --backends lmstudio --output-dir evals/eval-001

    # Filter specific models
    python3 -m Summarizer.eval google-alert.eml --models qwen3:latest mistral-7b --output-dir evals/eval-001
"""
from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import click
from dotenv import load_dotenv

# CRITICAL: Load .env BEFORE importing config module
# config.py reads environment variables during import, so .env must be loaded first
PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
load_dotenv(REPO_ROOT / '.env', override=True)

from .article_fetcher import FetchConfig, fetch_article, clear_cache, get_last_fetch_outcome
from .content_cleaner import extract_content
from .corpus_cache import save_corpus, iter_corpus, load_corpus
from .link_extractor import extract_links_from_eml
from .model_manager import get_available_models, load_lmstudio_model, unload_lmstudio_model, ModelInfo
from .summarizer import summarize_article, SummarizerConfig, SummarizerError
from .config import MAX_WORKERS


logger = logging.getLogger(__name__)


def generate_corpus(eml_path: Path, output_dir: Path) -> Path:
    """Generate corpus from alert email.

    Args:
        eml_path: Path to .eml file
        output_dir: Directory to save corpus

    Returns:
        Path to corpus directory

    Raises:
        RuntimeError: On unrecoverable corpus generation failure
    """
    logger.info("[corpus] Generating corpus from %s", eml_path)

    # Extract links
    records = extract_links_from_eml(eml_path)
    links = [
        {
            "title": record.title,
            "url": record.url,
            "publisher": getattr(record, "publisher", ""),
            "snippet": getattr(record, "snippet", ""),
        }
        for record in records
    ]
    logger.info("[corpus] Extracted %d links", len(links))

    # Fetch articles in parallel
    fetch_cfg = FetchConfig()
    articles: List[Dict] = []
    failures: List[str] = []

    def fetch_and_extract(link: Dict) -> Optional[Dict]:
        """Fetch and extract a single article."""
        url = link["url"]
        try:
            logger.info("[fetch] %s", url)
            html = fetch_article(url, fetch_cfg)

            outcome = get_last_fetch_outcome()
            if outcome:
                logger.info(
                    "[fetch][strategy=%s][format=%s][duration=%.2fs] %s",
                    outcome.strategy,
                    outcome.format,
                    outcome.duration,
                    url,
                )

            # Extract content
            if outcome and outcome.format == "html":
                content = extract_content(html)
            else:
                content = html  # Already Markdown

            if not content.strip():
                logger.error("[clean][ERROR] %s -> no content extracted", url)
                failures.append(url)
                return None

            # Validate content length
            word_count = len(content.split())
            if word_count < 100:
                logger.error("[clean][ERROR] %s -> insufficient content (%d words)", url, word_count)
                failures.append(url)
                return None

            return {
                "title": link["title"],
                "url": url,
                "publisher": link["publisher"],
                "snippet": link["snippet"],
                "content": content,
                "raw_html": html if outcome and outcome.format == "html" else "",
            }
        except Exception as exc:
            logger.error("[fetch][ERROR] %s -> %s", url, exc)
            failures.append(url)
            return None

    # Parallel fetch
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_and_extract, link): link for link in links}
        for future in as_completed(futures):
            result = future.result()
            if result:
                articles.append(result)

    if not articles:
        raise RuntimeError("No articles successfully fetched; cannot generate corpus")

    logger.info("[corpus] Successfully fetched %d/%d articles", len(articles), len(links))

    # Save corpus
    metadata = save_corpus(output_dir, eml_path.name, articles)
    corpus_dir = output_dir / "corpus"

    logger.info("[corpus] Saved to %s (hash: %s)", corpus_dir, metadata.corpus_hash[:8])

    if failures:
        logger.warning("[corpus] Failed to fetch %d articles: %s", len(failures), ", ".join(failures))

    return corpus_dir


def evaluate_model(model: ModelInfo, corpus_dir: Path, results_dir: Path) -> Dict:
    """Evaluate a single model against the corpus.

    Args:
        model: ModelInfo to evaluate
        corpus_dir: Path to corpus directory
        results_dir: Directory to write results

    Returns:
        Summary dict with metrics and summaries
    """
    logger.info("[eval] Evaluating model: %s (%s)", model.name, model.backend)

    # Load model if LM Studio
    if model.backend == "lmstudio" and not model.loaded:
        try:
            load_lmstudio_model(model.name)
        except Exception as exc:
            logger.error("[eval][ERROR] Failed to load %s: %s", model.name, exc)
            return {
                "model": model.name,
                "backend": model.backend,
                "articles_processed": 0,
                "avg_latency": 0.0,
                "errors": 1,
                "summaries": [],
                "error": f"Failed to load model: {exc}",
            }

    # Evaluate on corpus
    summaries: List[Dict] = []
    errors = 0
    total_duration = 0.0

    config = SummarizerConfig(model=model.name)

    for article in iter_corpus(corpus_dir):
        url = article["url"]
        logger.info("[eval] Summarizing: %s", url)

        start_time = time.time()
        try:
            summary = summarize_article(article, config=config, backend=model.backend)
            duration = time.time() - start_time
            total_duration += duration

            summary["duration"] = duration
            summaries.append(summary)

            logger.info("[eval] Success (%.2fs): %s", duration, url)
        except SummarizerError as exc:
            duration = time.time() - start_time
            total_duration += duration
            errors += 1

            logger.error("[eval][ERROR] Failed (%.2fs): %s -> %s", duration, url, exc)

            # Append error placeholder
            summaries.append({
                "title": article["title"],
                "url": url,
                "summary": [{"type": "error", "text": str(exc)}],
                "model": model.name,
                "duration": duration,
            })

    # Calculate metrics
    articles_processed = len(summaries)
    avg_latency = total_duration / articles_processed if articles_processed > 0 else 0.0

    result_dict = {
        "model": model.name,
        "backend": model.backend,
        "articles_processed": articles_processed,
        "avg_latency": avg_latency,
        "errors": errors,
        "summaries": summaries,
    }

    # Write model results
    model_filename = model.name.replace(":", "_").replace("/", "_")
    result_path = results_dir / f"{model_filename}.md"
    write_model_results(model.name, model.backend, result_dict, result_path)

    # Unload model if LM Studio
    if model.backend == "lmstudio":
        try:
            unload_lmstudio_model(model.name)
        except Exception as exc:
            logger.warning("[eval][WARN] Failed to unload %s: %s", model.name, exc)

    logger.info("[eval] Completed: %s (%d articles, %.2fs avg latency, %d errors)", model.name, articles_processed, avg_latency, errors)

    return result_dict


def write_model_results(model_name: str, backend: str, results: Dict, output_path: Path) -> None:
    """Write markdown report for a single model.

    Args:
        model_name: Model name
        backend: Backend name (lmstudio or ollama)
        results: Results dict from evaluate_model()
        output_path: Path to write markdown file
    """
    timestamp = datetime.now().isoformat()
    articles_processed = results["articles_processed"]
    avg_latency = results["avg_latency"]
    errors = results["errors"]
    summaries = results["summaries"]

    lines = [
        f"# Eval Results: {model_name} ({backend})",
        "",
        f"**Timestamp**: {timestamp}",
        f"**Articles**: {articles_processed}",
        f"**Avg Latency**: {avg_latency:.2f}s",
        f"**Errors**: {errors}",
        "",
        "---",
        "",
    ]

    for idx, summary in enumerate(summaries, start=1):
        title = summary.get("title", "Unknown")
        url = summary.get("url", "")
        duration = summary.get("duration", 0.0)
        summary_blocks = summary.get("summary", [])

        lines.append(f"## Article {idx}: {title}")
        lines.append("")
        lines.append(f"**URL**: {url}")
        lines.append("")

        # Check for errors
        is_error = any(block.get("type") == "error" for block in summary_blocks)
        if is_error:
            error_text = next((block.get("text", "Unknown error") for block in summary_blocks if block.get("type") == "error"), "Unknown error")
            lines.append(f"**Error**: {error_text}")
        else:
            lines.append("**Summary**:")
            for i, block in enumerate(summary_blocks, start=1):
                text = block.get("text", "")
                lines.append(f"{i}. {text}")

        lines.append("")
        lines.append(f"**Metrics**: {duration:.2f}s")
        lines.append("")
        lines.append("---")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("[eval] Wrote results: %s", output_path)


def generate_comparison_report(all_results: List[Dict], output_path: Path) -> None:
    """Generate comparison report across all models.

    Args:
        all_results: List of result dicts from evaluate_model()
        output_path: Path to write summary.md
    """
    timestamp = datetime.now().isoformat()

    # Determine corpus info from first result
    corpus_name = "unknown"
    article_count = 0
    if all_results:
        article_count = all_results[0]["articles_processed"]

    lines = [
        "# Multi-Model Eval Summary",
        "",
        f"**Timestamp**: {timestamp}",
        f"**Models Tested**: {len(all_results)}",
        f"**Articles**: {article_count}",
        "",
        "## Performance Comparison",
        "",
        "| Model | Backend | Avg Latency | Errors | Status |",
        "|-------|---------|-------------|--------|--------|",
    ]

    for result in all_results:
        model = result["model"]
        backend = result["backend"]
        avg_latency = result["avg_latency"]
        errors = result["errors"]
        status = "✓" if errors == 0 else f"⚠ ({errors})"

        lines.append(f"| {model} | {backend} | {avg_latency:.2f}s | {errors} | {status} |")

    lines.append("")
    lines.append("## Side-by-Side Examples")
    lines.append("")

    # Show first 3 articles side-by-side
    max_examples = min(3, article_count)
    for article_idx in range(max_examples):
        # Get article info from first result
        if not all_results or article_idx >= len(all_results[0]["summaries"]):
            continue

        article = all_results[0]["summaries"][article_idx]
        title = article.get("title", "Unknown")
        url = article.get("url", "")

        lines.append(f"### Article {article_idx + 1}: {title}")
        lines.append("")
        lines.append(f"**URL**: {url}")
        lines.append("")

        # Show summaries from each model
        for result in all_results:
            model = result["model"]
            summaries = result["summaries"]

            if article_idx >= len(summaries):
                continue

            summary = summaries[article_idx]
            summary_blocks = summary.get("summary", [])

            lines.append(f"**{model}**:")

            # Check for errors
            is_error = any(block.get("type") == "error" for block in summary_blocks)
            if is_error:
                error_text = next((block.get("text", "Unknown error") for block in summary_blocks if block.get("type") == "error"), "Unknown error")
                lines.append(f"- *Error: {error_text}*")
            else:
                for i, block in enumerate(summary_blocks, start=1):
                    text = block.get("text", "")
                    lines.append(f"{i}. {text}")

            lines.append("")

        lines.append("---")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("[eval] Wrote comparison report: %s", output_path)


@click.command()
@click.argument("eml_path", type=click.Path(exists=True), required=False)
@click.option("--corpus-only", is_flag=True, help="Generate corpus and exit")
@click.option("--corpus-dir", type=click.Path(exists=True), help="Reuse existing corpus")
@click.option("--backends", multiple=True, type=click.Choice(["lmstudio", "ollama"]), help="Filter backends (default: both)")
@click.option("--models", multiple=True, help="Filter specific models (default: all)")
@click.option("--output-dir", type=click.Path(), help="Override default evals/eval-TIMESTAMP")
def eval_cmd(eml_path, corpus_only, corpus_dir, backends, models, output_dir):
    """Multi-model evaluation for Summarizer."""

    # Validation: require eml_path OR corpus_dir (not both, not neither)
    if bool(eml_path) == bool(corpus_dir):
        raise click.UsageError("Provide either EML_PATH or --corpus-dir (not both, not neither)")

    # Validation: --corpus-only requires eml_path
    if corpus_only and not eml_path:
        raise click.UsageError("--corpus-only requires EML_PATH")

    # Determine output directory
    if output_dir:
        output_path = Path(output_dir).expanduser().resolve()
    else:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_path = Path(__file__).parent / "evals" / f"eval-{timestamp}"

    output_path.mkdir(parents=True, exist_ok=True)
    results_dir = output_path / "results"
    results_dir.mkdir(exist_ok=True)

    # Setup logging
    log_file = output_path / "eval.log"
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )

    logger.info("=" * 80)
    logger.info("Multi-Model Evaluation")
    logger.info("=" * 80)
    logger.info("Output directory: %s", output_path)

    # Generate or load corpus
    if corpus_dir:
        corpus_path = Path(corpus_dir).expanduser().resolve()
        logger.info("[corpus] Using existing corpus: %s", corpus_path)

        # Validate corpus
        try:
            metadata, _ = load_corpus(corpus_path)
            logger.info("[corpus] Loaded %d articles (hash: %s)", metadata.article_count, metadata.corpus_hash[:8])
        except ValueError as exc:
            raise click.ClickException(f"Invalid corpus directory: {exc}")
    else:
        eml_file = Path(eml_path).expanduser().resolve()
        logger.info("[corpus] Generating corpus from: %s", eml_file)

        clear_cache()

        try:
            corpus_path = generate_corpus(eml_file, output_path)
        except RuntimeError as exc:
            raise click.ClickException(f"Corpus generation failed: {exc}")

        if corpus_only:
            logger.info("[corpus] Corpus generation complete (--corpus-only)")
            click.echo(f"Corpus saved to: {corpus_path}")
            return

    # Discover models
    backend_filter = list(backends) if backends else ["lmstudio", "ollama"]
    logger.info("[models] Discovering models (backends: %s)", ", ".join(backend_filter))

    available_models = get_available_models(backend_filter)

    if not available_models:
        raise click.ClickException(f"No models found for backends: {', '.join(backend_filter)}")

    # Filter models if specified
    if models:
        model_filter = set(models)
        available_models = [m for m in available_models if m.name in model_filter]

        if not available_models:
            raise click.ClickException(f"No matching models found: {', '.join(models)}")

    logger.info("[models] Evaluating %d models:", len(available_models))
    for model in available_models:
        logger.info("  - %s (%s)%s", model.name, model.backend, " [loaded]" if model.loaded else "")

    # Evaluate each model
    all_results: List[Dict] = []
    for idx, model in enumerate(available_models, start=1):
        logger.info("")
        logger.info("[%d/%d] Evaluating: %s (%s)", idx, len(available_models), model.name, model.backend)
        logger.info("-" * 80)

        result = evaluate_model(model, corpus_path, results_dir)
        all_results.append(result)

    # Generate comparison report
    logger.info("")
    logger.info("=" * 80)
    logger.info("Generating comparison report")
    logger.info("=" * 80)

    summary_path = results_dir / "summary.md"
    generate_comparison_report(all_results, summary_path)

    # Print summary to console
    click.echo("")
    click.echo("=" * 80)
    click.echo("Evaluation Complete")
    click.echo("=" * 80)
    click.echo(f"Output directory: {output_path}")
    click.echo(f"Comparison report: {summary_path}")
    click.echo("")
    click.echo("Model Performance:")
    for result in all_results:
        model = result["model"]
        backend = result["backend"]
        avg_latency = result["avg_latency"]
        errors = result["errors"]
        status = "✓" if errors == 0 else f"⚠ {errors} errors"
        click.echo(f"  {model:30} ({backend:9}) {avg_latency:6.2f}s  {status}")


if __name__ == "__main__":
    eval_cmd()
