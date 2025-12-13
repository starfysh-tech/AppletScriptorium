"""Article extraction benchmark framework."""
from .extractors import (
    ArticleExtractor,
    ExtractionResult,
    ReadabilityLxmlExtractor,
    TrafilaturaExtractor,
    ReadabilipyExtractor,
    Newspaper3kExtractor,
    get_all_extractors,
)
from .test_urls import TEST_URLS, TestURL, get_urls_by_category, get_priority_urls
from .metrics import QualityMetrics, evaluate_quality
from .evaluator import ExtractionBenchmark, URLBenchmarkResult
from .report import generate_markdown_report

__all__ = [
    "ArticleExtractor",
    "ExtractionResult",
    "ReadabilityLxmlExtractor",
    "TrafilaturaExtractor",
    "ReadabilipyExtractor",
    "Newspaper3kExtractor",
    "get_all_extractors",
    "TEST_URLS",
    "TestURL",
    "get_urls_by_category",
    "get_priority_urls",
    "QualityMetrics",
    "evaluate_quality",
    "ExtractionBenchmark",
    "URLBenchmarkResult",
    "generate_markdown_report",
]
