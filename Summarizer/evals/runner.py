"""Model evaluation runner for testing different LLM models."""

import httpx
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import json

from ..summarizer import summarize_article, SummarizerConfig
from ..config import LMSTUDIO_BASE_URL
from ..model_manager import LMS, discover_lmstudio_models, load_lmstudio_model, unload_all_lmstudio_models
from .metrics import (
    evaluate_accuracy,
    evaluate_consistency,
    detect_hallucinations,
    AccuracyMetrics,
    ConsistencyMetrics,
    HallucinationMetrics,
)
from .gold_standard import get_annotation_by_url

logger = logging.getLogger(__name__)


@dataclass
class ModelResults:
    """Evaluation results for a single model."""

    model: str
    accuracy_scores: List[AccuracyMetrics] = field(default_factory=list)
    consistency_scores: List[ConsistencyMetrics] = field(default_factory=list)
    hallucination_scores: List[HallucinationMetrics] = field(default_factory=list)
    error_count: int = 0
    total_articles: int = 0
    runs_per_article: int = 1

    @property
    def avg_accuracy(self) -> float:
        """Calculate average accuracy score across all articles."""
        if not self.accuracy_scores:
            return 0.0
        scores = [m.accuracy_score for m in self.accuracy_scores]
        return sum(scores) / len(scores)

    @property
    def avg_consistency(self) -> float:
        """Calculate average consistency score across all articles."""
        if not self.consistency_scores:
            return 0.0
        scores = [m.consistency_score for m in self.consistency_scores]
        return sum(scores) / len(scores)

    @property
    def hallucination_rate(self) -> float:
        """Calculate proportion of summaries with hallucinations."""
        if not self.hallucination_scores:
            return 0.0
        has_hallucinations = [m.has_hallucinations for m in self.hallucination_scores]
        return sum(has_hallucinations) / len(has_hallucinations)

    @property
    def success_rate(self) -> float:
        """Proportion of attempted summaries (articles x runs) that succeeded."""
        attempts = self.total_articles * self.runs_per_article
        return (attempts - self.error_count) / attempts if attempts else 0.0


class ModelEvaluator:
    """Evaluates LLM models on the summarization task."""

    def __init__(self):
        """Initialize evaluator.

        Talks to the LM Studio instance configured by LMSTUDIO_BASE_URL (the
        summarizer reads the same setting, so there is no per-instance override).
        """
        self.lmstudio_url = LMSTUDIO_BASE_URL
        if not self.lmstudio_url:
            raise ValueError("LM Studio URL not configured. Set LMSTUDIO_BASE_URL in .env")

        # model_manager resolves the CLI to ~/.lmstudio/bin/lms or PATH
        if not shutil.which(LMS):
            raise ValueError(f"LM Studio CLI not found at {LMS}")

    def get_available_models(self) -> List[str]:
        """Get list of available models from LM Studio.

        Returns:
            List of model identifiers available in LM Studio
        """
        models_info = discover_lmstudio_models()
        return [m.name for m in models_info]

    def load_model(self, model: str) -> bool:
        """Load a specific model in LM Studio.

        Unloads all currently loaded models first to ensure resources are available.

        Args:
            model: Model identifier to load

        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            # Unload all models first to free resources
            unload_all_lmstudio_models()
        except Exception as exc:
            logger.warning("Failed to unload models before loading %s: %s", model, exc)

        try:
            load_lmstudio_model(model)
            logger.info("Successfully loaded model: %s", model)
            return True
        except subprocess.CalledProcessError as exc:
            logger.error("Failed to load model %s: %s", model, exc.stderr)
            return False
        except subprocess.TimeoutExpired:
            logger.error("Loading model %s timed out", model)
            return False
        except Exception as exc:
            logger.error("Error loading model %s: %s", model, exc)
            return False

    def evaluate_model(
        self,
        model: str,
        articles: List[dict],
        runs: int = 1,
    ) -> ModelResults:
        """Evaluate a model on a set of articles.

        Args:
            model: Model identifier to evaluate
            articles: List of article dicts with "url", "title", "content" keys
            runs: Number of times to run each article (for consistency testing)

        Returns:
            ModelResults object with evaluation metrics
        """
        if runs < 1:
            raise ValueError(f"runs must be >= 1, got {runs}")
        logger.info("Evaluating model: %s (runs=%d, articles=%d)", model, runs, len(articles))

        # Load model
        if not self.load_model(model):
            logger.error("Failed to load model %s, skipping evaluation", model)
            return ModelResults(model=model, total_articles=len(articles), error_count=len(articles))

        results = ModelResults(model=model, total_articles=len(articles), runs_per_article=runs)

        # For each article, run multiple times
        for article in articles:
            url = article.get("url", "")
            logger.info("Evaluating article: %s", url)

            gold = get_annotation_by_url(url)
            if not gold:
                logger.warning("No gold standard for %s, skipping", url)
                results.error_count += 1
                continue

            # Run summarization multiple times
            summaries = []
            for run_idx in range(runs):
                try:
                    config = SummarizerConfig(model=model)
                    summary = summarize_article(
                        article,
                        config=config,
                        backend="lmstudio",  # Force LM Studio backend
                    )
                    summaries.append(summary)
                    logger.info("Run %d/%d completed for %s", run_idx + 1, runs, url)
                except Exception as exc:
                    logger.error("Run %d/%d failed for %s: %s", run_idx + 1, runs, url, exc)
                    results.error_count += 1

            if not summaries:
                logger.warning("All runs failed for %s", url)
                continue

            # Evaluate accuracy (using first run)
            summary = summaries[0]
            article_content = article.get("content", "")

            accuracy = evaluate_accuracy(summary, gold, article_content)
            results.accuracy_scores.append(accuracy)

            # Detect hallucinations (using first run)
            hallucination = detect_hallucinations(summary, article_content, gold)
            results.hallucination_scores.append(hallucination)

            # Evaluate consistency (if multiple runs)
            if len(summaries) > 1:
                consistency = evaluate_consistency(summaries)
                results.consistency_scores.append(consistency)

        logger.info(
            "Model %s evaluation complete: accuracy=%.2f, consistency=%.2f, hallucination_rate=%.2f, success_rate=%.2f",
            model,
            results.avg_accuracy,
            results.avg_consistency,
            results.hallucination_rate,
            results.success_rate,
        )

        return results

    def evaluate_all_models(
        self,
        articles: List[dict],
        runs: int = 3,
    ) -> dict[str, ModelResults]:
        """Evaluate all available models.

        Args:
            articles: List of article dicts with "url", "title", "content" keys
            runs: Number of times to run each article (for consistency testing)

        Returns:
            Dict mapping model name to ModelResults
        """
        models = self.get_available_models()
        if not models:
            logger.error("No models available in LM Studio")
            return {}

        logger.info("Found %d models to evaluate", len(models))

        results = {}
        for model in models:
            try:
                model_results = self.evaluate_model(model, articles, runs=runs)
                results[model] = model_results
            except Exception as exc:
                logger.error("Failed to evaluate model %s: %s", model, exc)
                results[model] = ModelResults(
                    model=model,
                    total_articles=len(articles),
                    error_count=len(articles),
                )

        return results


def load_test_articles(articles_dir: Path = None) -> List[dict]:
    """Load test articles from gold standard annotations.

    Args:
        articles_dir: Directory containing article content files (defaults to runs/)

    Returns:
        List of article dicts with "url", "title", "content" keys
    """
    from .load_articles import load_articles_from_directory, load_articles_from_runs

    if articles_dir is not None:
        return load_articles_from_directory(articles_dir)
    else:
        return load_articles_from_runs()
