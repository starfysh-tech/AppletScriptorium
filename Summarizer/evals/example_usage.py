"""Example usage of the model evaluation framework.

This script demonstrates how to use the evaluation framework programmatically
without using the CLI.
"""

import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)

# Import evaluation components
from Summarizer.evals import ModelEvaluator, GOLD_ANNOTATIONS
from Summarizer.evals.load_articles import load_articles_from_runs
from Summarizer.evals.report import save_report

def main():
    """Run example evaluation."""

    print("=" * 80)
    print("Model Evaluation Framework - Example Usage")
    print("=" * 80)
    print()

    # Step 1: Initialize evaluator
    print("Step 1: Initialize evaluator")
    try:
        evaluator = ModelEvaluator()
        print(f"  ✓ Evaluator initialized (LM Studio URL: {evaluator.lmstudio_url})")
    except ValueError as e:
        print(f"  ✗ Failed to initialize: {e}")
        return 1

    # Step 2: Get available models
    print("\nStep 2: Get available models")
    models = evaluator.get_available_models()
    if not models:
        print("  ✗ No models available")
        return 1

    print(f"  ✓ Found {len(models)} models:")
    for i, model in enumerate(models[:5], 1):  # Show first 5
        print(f"    {i}. {model}")
    if len(models) > 5:
        print(f"    ... and {len(models) - 5} more")

    # Step 3: Load test articles
    print("\nStep 3: Load test articles")
    articles = load_articles_from_runs()
    if not articles:
        print("  ✗ No articles loaded")
        return 1

    print(f"  ✓ Loaded {len(articles)} articles from gold standard:")
    for i, article in enumerate(articles, 1):
        print(f"    {i}. {article['title'][:60]}")

    # Step 4: Evaluate first model (or specific model)
    print("\nStep 4: Evaluate model")
    test_model = models[0]  # Use first available model
    # Or specify a model: test_model = "llama-chat-summary-3.2-3b"

    print(f"  Evaluating: {test_model}")
    print(f"  Running {3} passes per article...")

    results = evaluator.evaluate_model(
        model=test_model,
        articles=articles,
        runs=3,  # 3 runs for consistency testing
    )

    # Step 5: Display results
    print("\nStep 5: Results")
    print(f"  Model: {results.model}")
    print(f"  Articles: {results.total_articles}")
    print(f"  Errors: {results.error_count}")
    print()
    print("  Metrics:")
    print(f"    Accuracy:          {results.avg_accuracy:.1%}")
    print(f"    Consistency:       {results.avg_consistency:.1%}")
    print(f"    Hallucination Rate: {results.hallucination_rate:.1%}")
    print(f"    Success Rate:      {results.success_rate:.1%}")

    # Step 6: Generate report
    print("\nStep 6: Generate report")
    output_path = Path("example_eval_report.md")
    save_report({test_model: results}, output_path)
    print(f"  ✓ Report saved to: {output_path}")

    print("\n" + "=" * 80)
    print("Example complete! Check example_eval_report.md for detailed results.")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())
