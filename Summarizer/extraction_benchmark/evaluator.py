"""Benchmark orchestration - runs extractors against test URLs."""
from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import httpx

from .extractors import ArticleExtractor, ExtractionResult, get_all_extractors
from .test_urls import TEST_URLS, TestURL
from .metrics import QualityMetrics, evaluate_quality

logger = logging.getLogger(__name__)


@dataclass
class URLBenchmarkResult:
    """Results for all extractors on a single URL."""
    test_url: TestURL
    html_fetch_duration: float
    html_size: int
    results: Dict[str, ExtractionResult] = field(default_factory=dict)
    metrics: Dict[str, QualityMetrics] = field(default_factory=dict)
    winner: Optional[str] = None  # Name of best extractor

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "url": self.test_url.url,
            "domain": self.test_url.domain,
            "category": self.test_url.category,
            "html_fetch_duration": self.html_fetch_duration,
            "html_size": self.html_size,
            "results": {
                name: {
                    "content_preview": result.content[:200] if result.content else "",
                    "word_count": result.word_count,
                    "duration": result.duration,
                    "success": result.success,
                    "error": result.error,
                }
                for name, result in self.results.items()
            },
            "metrics": {
                name: {
                    "word_count": m.word_count,
                    "is_valid": m.is_valid,
                    "quality_score": m.quality_score,
                    "is_paywall": m.is_paywall,
                    "is_ui_elements": m.is_ui_elements,
                    "is_references_only": m.is_references_only,
                }
                for name, m in self.metrics.items()
            },
            "winner": self.winner,
        }


class ExtractionBenchmark:
    """Orchestrates benchmark runs across extractors and URLs."""

    def __init__(
        self,
        output_dir: Path,
        extractors: Optional[List[ArticleExtractor]] = None,
        test_urls: Optional[List[TestURL]] = None,
        http_timeout: float = 30.0,
    ):
        """Initialize benchmark.

        Args:
            output_dir: Directory to store results and cached HTML
            extractors: List of extractors to test (default: all available)
            test_urls: List of URLs to test (default: TEST_URLS)
            http_timeout: Timeout for fetching HTML
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.extractors = extractors or get_all_extractors()
        self.test_urls = test_urls or TEST_URLS
        self.http_timeout = http_timeout

        # Cache directory for HTML
        self.html_cache_dir = self.output_dir / "html_cache"
        self.html_cache_dir.mkdir(exist_ok=True)

        # Results
        self.results: List[URLBenchmarkResult] = []

    def _url_to_cache_path(self, url: str) -> Path:
        """Generate cache file path for a URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return self.html_cache_dir / f"{url_hash}.html"

    def _fetch_html(self, url: str) -> tuple[str, float]:
        """Fetch HTML for a URL, using cache if available.

        Returns:
            Tuple of (html_content, fetch_duration)
        """
        cache_path = self._url_to_cache_path(url)

        # Check cache first
        if cache_path.exists():
            logger.debug("[fetch] Using cached HTML for %s", url)
            return cache_path.read_text(encoding="utf-8"), 0.0

        # Fetch from network
        start = time.perf_counter()
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            response = httpx.get(url, headers=headers, timeout=self.http_timeout, follow_redirects=True)
            response.raise_for_status()
            html = response.text
            duration = time.perf_counter() - start

            # Cache for future runs
            cache_path.write_text(html, encoding="utf-8")
            logger.info("[fetch] Fetched %s (%d bytes, %.2fs)", url, len(html), duration)

            return html, duration
        except Exception as exc:
            logger.error("[fetch] Failed to fetch %s: %s", url, exc)
            return "", time.perf_counter() - start

    def benchmark_url(self, test_url: TestURL) -> URLBenchmarkResult:
        """Run all extractors on a single URL.

        Args:
            test_url: TestURL to benchmark

        Returns:
            URLBenchmarkResult with all extractor results
        """
        logger.info("[benchmark] Testing %s (%s)", test_url.url, test_url.category)

        # Fetch HTML once
        html, fetch_duration = self._fetch_html(test_url.url)

        result = URLBenchmarkResult(
            test_url=test_url,
            html_fetch_duration=fetch_duration,
            html_size=len(html),
        )

        if not html:
            logger.warning("[benchmark] No HTML fetched for %s", test_url.url)
            return result

        # Run each extractor
        best_score = -1.0
        for extractor in self.extractors:
            logger.debug("[benchmark] Running %s on %s", extractor.name, test_url.url)

            extraction = extractor.extract(html, test_url.url)
            metrics = evaluate_quality(extraction.content)

            result.results[extractor.name] = extraction
            result.metrics[extractor.name] = metrics

            # Track winner by quality score
            if metrics.quality_score > best_score:
                best_score = metrics.quality_score
                result.winner = extractor.name

        return result

    def run_benchmark(self) -> List[URLBenchmarkResult]:
        """Run benchmark across all test URLs.

        Returns:
            List of URLBenchmarkResult for each URL
        """
        logger.info(
            "[benchmark] Starting benchmark: %d extractors, %d URLs",
            len(self.extractors),
            len(self.test_urls),
        )

        self.results = []
        for i, test_url in enumerate(self.test_urls, 1):
            logger.info("[benchmark] Progress: %d/%d", i, len(self.test_urls))
            url_result = self.benchmark_url(test_url)
            self.results.append(url_result)

        # Save raw results to JSON
        results_path = self.output_dir / "results.json"
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "extractors": [e.name for e in self.extractors],
                    "results": [r.to_dict() for r in self.results],
                },
                f,
                indent=2,
            )
        logger.info("[benchmark] Results saved to %s", results_path)

        return self.results
