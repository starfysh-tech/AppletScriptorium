"""Generate human-readable benchmark reports."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import List, Dict

from .evaluator import URLBenchmarkResult
from .test_urls import URLCategory


def generate_markdown_report(
    results: List[URLBenchmarkResult],
    output_path: Path,
) -> str:
    """Generate a Markdown benchmark report.

    Args:
        results: List of URLBenchmarkResult from benchmark run
        output_path: Path to write report.md

    Returns:
        Report content as string
    """
    lines = ["# Article Extraction Benchmark Report\n"]

    # Collect all extractor names
    extractor_names = set()
    for r in results:
        extractor_names.update(r.results.keys())
    extractor_names = sorted(extractor_names)

    # === Summary Table ===
    lines.append("## Summary Rankings\n")
    lines.append("| Extractor | Success Rate | Avg Words | Avg Quality | Avg Duration |")
    lines.append("|-----------|--------------|-----------|-------------|--------------|")

    # Compute aggregate stats per extractor
    extractor_stats: Dict[str, dict] = {}
    for name in extractor_names:
        successes = 0
        total = 0
        word_counts = []
        quality_scores = []
        durations = []

        for r in results:
            if name in r.results:
                total += 1
                extraction = r.results[name]
                metrics = r.metrics.get(name)

                if metrics and metrics.is_valid:
                    successes += 1
                if extraction.word_count > 0:
                    word_counts.append(extraction.word_count)
                if metrics:
                    quality_scores.append(metrics.quality_score)
                durations.append(extraction.duration)

        extractor_stats[name] = {
            "success_rate": (successes / total * 100) if total > 0 else 0,
            "avg_words": sum(word_counts) / len(word_counts) if word_counts else 0,
            "avg_quality": sum(quality_scores) / len(quality_scores) if quality_scores else 0,
            "avg_duration": sum(durations) / len(durations) if durations else 0,
        }

    # Sort by success rate descending
    sorted_extractors = sorted(
        extractor_names,
        key=lambda n: extractor_stats[n]["success_rate"],
        reverse=True,
    )

    for name in sorted_extractors:
        stats = extractor_stats[name]
        lines.append(
            f"| {name} | {stats['success_rate']:.1f}% | "
            f"{stats['avg_words']:.0f} | {stats['avg_quality']:.2f} | "
            f"{stats['avg_duration']:.3f}s |"
        )

    # === Results by Category ===
    lines.append("\n## Results by Category\n")

    categories: Dict[str, List[URLBenchmarkResult]] = defaultdict(list)
    for r in results:
        categories[r.test_url.category].append(r)

    for category in sorted(categories.keys()):
        cat_results = categories[category]
        lines.append(f"### {category.replace('_', ' ').title()}\n")
        lines.append("| URL | Winner | " + " | ".join(extractor_names) + " |")
        lines.append("|-----|--------|" + "|".join(["---"] * len(extractor_names)) + "|")

        for r in cat_results:
            # Truncate URL for display
            url_display = r.test_url.url
            if len(url_display) > 50:
                url_display = url_display[:47] + "..."

            cells = [f"`{url_display}`", r.winner or "none"]
            for name in extractor_names:
                if name in r.metrics:
                    m = r.metrics[name]
                    if m.is_valid:
                        cells.append(f"✓ {m.word_count}w")
                    else:
                        reason = []
                        if m.is_paywall:
                            reason.append("paywall")
                        if m.is_ui_elements:
                            reason.append("UI")
                        if m.is_references_only:
                            reason.append("refs")
                        if m.word_count < 100:
                            reason.append(f"{m.word_count}w")
                        cells.append(f"✗ {','.join(reason)}")
                else:
                    cells.append("n/a")
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    # === Recommendations ===
    lines.append("## Recommendations\n")

    # Find best overall extractor
    best_extractor = sorted_extractors[0] if sorted_extractors else None
    if best_extractor:
        stats = extractor_stats[best_extractor]
        lines.append(f"### Recommended Primary Extractor: `{best_extractor}`\n")
        lines.append(f"- Success Rate: {stats['success_rate']:.1f}%")
        lines.append(f"- Avg Quality Score: {stats['avg_quality']:.2f}")
        lines.append(f"- Avg Extraction Time: {stats['avg_duration']:.3f}s")

        # Check if it beats baseline
        baseline_stats = extractor_stats.get("readability-lxml", {})
        if baseline_stats:
            improvement = stats["success_rate"] - baseline_stats.get("success_rate", 0)
            lines.append(f"\n**vs. readability-lxml baseline: {improvement:+.1f}% success rate**")
            if improvement >= 20:
                lines.append("\n✓ **Recommend replacing readability-lxml** (≥20% improvement)")
            else:
                lines.append("\n⚠ **Keep readability-lxml** (<20% improvement)")

    # Write report
    report_content = "\n".join(lines)
    output_path.write_text(report_content, encoding="utf-8")

    return report_content
