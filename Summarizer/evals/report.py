"""Report generation for model evaluation results."""

from pathlib import Path
from typing import Dict
from .runner import ModelResults, format_score, ranked_by_accuracy


def _best(results: Dict[str, ModelResults], metric: str, lowest: bool = False) -> str:
    """`model` (score) for the best scored model on `metric`, or "n/a" if none was scored."""
    scored = [r for r in results.values() if getattr(r, metric) is not None]
    if not scored:
        return "n/a"
    pick = (min if lowest else max)(scored, key=lambda r: getattr(r, metric))
    return f"`{pick.model}` ({format_score(getattr(pick, metric))})"


def generate_markdown_report(results: Dict[str, ModelResults]) -> str:
    """Generate markdown comparison report for model evaluation.

    Args:
        results: Dict mapping model name to ModelResults

    Returns:
        Markdown-formatted report string
    """
    if not results:
        return "# Model Evaluation Report\n\nNo results to report.\n"

    # Sort models by accuracy (descending)
    sorted_models = ranked_by_accuracy(results)

    lines = [
        "# Model Evaluation Report",
        "",
        f"Evaluated {len(results)} models across {sorted_models[0][1].total_articles} articles.",
        "",
        "## Summary Rankings",
        "",
        "| Rank | Model | Accuracy | Consistency | Hallucination Rate | Success Rate |",
        "|------|-------|----------|-------------|-------------------|--------------|",
    ]

    for rank, (model, model_results) in enumerate(sorted_models, 1):
        lines.append(
            f"| {rank} | `{model}` | "
            f"{format_score(model_results.avg_accuracy)} | "
            f"{format_score(model_results.avg_consistency)} | "
            f"{format_score(model_results.hallucination_rate)} | "
            f"{format_score(model_results.success_rate)} |"
        )

    lines.extend([
        "",
        "## Detailed Results",
        "",
    ])

    lines.extend([
        "### Best Performers",
        "",
        f"- **Best Accuracy**: {_best(results, 'avg_accuracy')}",
        f"- **Best Consistency**: {_best(results, 'avg_consistency')}",
        f"- **Lowest Hallucination Rate**: {_best(results, 'hallucination_rate', lowest=True)}",
        f"- **Best Success Rate**: {_best(results, 'success_rate')}",
        "",
    ])

    # Detailed breakdown per model
    for model, model_results in sorted_models:
        lines.extend([
            f"### Model: `{model}`",
            "",
            "**Overall Metrics:**",
            "",
            f"- Accuracy Score: {format_score(model_results.avg_accuracy)}",
            f"- Consistency Score: {format_score(model_results.avg_consistency)}",
            f"- Hallucination Rate: {format_score(model_results.hallucination_rate)}",
            f"- Success Rate: {format_score(model_results.success_rate)}",
            f"- Errors: {model_results.error_count}/{model_results.total_articles * model_results.runs_per_article} runs",
            "",
        ])

        # Accuracy breakdown
        if model_results.accuracy_scores:
            lines.extend([
                "**Accuracy Breakdown:**",
                "",
            ])

            # Compute averages for each accuracy component
            has_4_bullets = sum(m.has_4_bullets for m in model_results.accuracy_scores)
            labels_match = sum(m.labels_match_type for m in model_results.accuracy_scores)
            actionability_valid = sum(m.actionability_valid for m in model_results.accuracy_scores)
            actionability_correct = sum(m.actionability_correct for m in model_results.accuracy_scores)
            # None when the summary did not report its classified type
            type_checked = [m.article_type_correct for m in model_results.accuracy_scores
                            if m.article_type_correct is not None]
            tag_selected = sum(m.tag_selected for m in model_results.accuracy_scores)
            avg_facts = sum(m.facts_present for m in model_results.accuracy_scores)

            total = len(model_results.accuracy_scores)

            lines.extend([
                f"- Has 4 bullets: {has_4_bullets}/{total} ({has_4_bullets/total:.1%})",
                f"- Labels match type: {labels_match}/{total} ({labels_match/total:.1%})",
                f"- Actionability valid: {actionability_valid}/{total} ({actionability_valid/total:.1%})",
                f"- Actionability matches gold: {actionability_correct}/{total} ({actionability_correct/total:.1%})",
                f"- Tag selected (not placeholder): {tag_selected}/{total} ({tag_selected/total:.1%})",
            ])
            if type_checked:
                type_ok = sum(type_checked)
                lines.append(
                    f"- Article type matches gold: {type_ok}/{len(type_checked)} ({type_ok/len(type_checked):.1%})"
                )
            lines.extend([
                f"- Average fact coverage: {avg_facts/total:.1%}",
                "",
            ])

        # Hallucination breakdown
        if model_results.hallucination_scores:
            lines.extend([
                "**Hallucination Breakdown:**",
                "",
            ])

            concern_fabricated = sum(m.concern_is_fabricated for m in model_results.hallucination_scores)
            concern_benefit = sum(m.concern_is_benefit for m in model_results.hallucination_scores)
            concern_duplicate = sum(m.concern_duplicates_other for m in model_results.hallucination_scores)
            invented_numbers = sum(m.invented_numbers for m in model_results.hallucination_scores)

            total = len(model_results.hallucination_scores)

            lines.extend([
                f"- Fabricated concerns: {concern_fabricated}/{total} ({concern_fabricated/total:.1%})",
                f"- Concern is benefit: {concern_benefit}/{total} ({concern_benefit/total:.1%})",
                f"- Concern duplicates other bullet: {concern_duplicate}/{total} ({concern_duplicate/total:.1%})",
                f"- Invented numbers: {invented_numbers}/{total} ({invented_numbers/total:.1%})",
                "",
            ])

        # Consistency breakdown
        if model_results.consistency_scores:
            lines.extend([
                "**Consistency Breakdown:**",
                "",
            ])

            structure_identical = sum(m.structure_identical for m in model_results.consistency_scores)
            actionability_stable = sum(m.actionability_stable for m in model_results.consistency_scores)
            avg_similarity = sum(m.content_similarity for m in model_results.consistency_scores)

            total = len(model_results.consistency_scores)

            lines.extend([
                f"- Structure identical: {structure_identical}/{total} ({structure_identical/total:.1%})",
                f"- Actionability stable: {actionability_stable}/{total} ({actionability_stable/total:.1%})",
                f"- Average content similarity: {avg_similarity/total:.1%}",
                "",
            ])

        lines.append("---")
        lines.append("")

    # Add interpretation guide
    lines.extend([
        "## Interpretation Guide",
        "",
        "### Metrics Explained",
        "",
        "**Accuracy Score** (higher is better):",
        "- Measures structural correctness and fact coverage",
        "- Weighted: 50% structure (bullets, labels, tags, actionability format and category, article type when reported) + 50% content (facts)",
        "",
        "**Consistency Score** (higher is better):",
        "- Measures output stability across multiple runs",
        "- Models with high consistency produce similar outputs for the same input",
        "",
        "**Hallucination Rate** (lower is better):",
        "- Proportion of summaries with fabricated content",
        "- Checks for invented concerns, misclassified benefits, duplicates, and invented numbers",
        "",
        "**Success Rate** (higher is better):",
        "- Proportion of runs (gold-annotated articles x runs) that produced a summary",
        "- Models with low success rates may timeout or fail frequently",
        "",
        "### Common Issues to Look For",
        "",
        "1. **Placeholder tags** (`[🚀/🗺️/👀]`): Model failed to select specific tag",
        "2. **Fabricated concerns**: Model invented concerns not in article",
        "3. **Benefits as concerns**: Model misclassified positive outcomes as concerns",
        "4. **Empty actionability**: Model failed to generate actionability indicator",
        "5. **Low fact coverage**: Summary missing key information from article",
        "",
    ])

    return "\n".join(lines)


def save_report(results: Dict[str, ModelResults], output_path: str | Path) -> None:
    """Save evaluation report to file.

    Args:
        results: Dict mapping model name to ModelResults
        output_path: Path to save report (markdown format)
    """
    report = generate_markdown_report(results)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Report saved to {output_path}")
