"""Extractor interface and implementations for benchmark testing."""
from __future__ import annotations

import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Type

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExtractionResult:
    """Result of a single extraction attempt."""
    content: str
    word_count: int
    duration: float  # seconds
    success: bool
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class ArticleExtractor(ABC):
    """Abstract base class for article extractors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this extractor."""
        pass

    @abstractmethod
    def extract(self, html: str, url: str = "") -> ExtractionResult:
        """Extract article content from HTML.

        Args:
            html: Raw HTML string
            url: Original URL (some extractors use this for hints)

        Returns:
            ExtractionResult with content and metadata
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this extractor's dependencies are installed."""
        pass


class ReadabilityLxmlExtractor(ArticleExtractor):
    """Baseline extractor using readability-lxml (current production)."""

    @property
    def name(self) -> str:
        return "readability-lxml"

    def is_available(self) -> bool:
        try:
            from readability import Document
            return True
        except ImportError:
            return False

    def extract(self, html: str, url: str = "") -> ExtractionResult:
        start = time.perf_counter()
        try:
            # Import here to match production behavior
            from readability import Document
            from bs4 import BeautifulSoup
            import markdownify

            doc = Document(html)
            main_html = doc.summary(html_partial=True)

            # Clean with BeautifulSoup (matches content_cleaner.py)
            soup = BeautifulSoup(main_html, "html.parser")
            for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            # Convert to text
            text = soup.get_text(separator="\n", strip=True)
            word_count = len(text.split())

            return ExtractionResult(
                content=text,
                word_count=word_count,
                duration=time.perf_counter() - start,
                success=word_count >= 50,
                metadata={"title": doc.title()},
            )
        except Exception as exc:
            return ExtractionResult(
                content="",
                word_count=0,
                duration=time.perf_counter() - start,
                success=False,
                error=str(exc),
            )


class TrafilaturaExtractor(ArticleExtractor):
    """Trafilatura extractor - optimized for news articles."""

    @property
    def name(self) -> str:
        return "trafilatura"

    def is_available(self) -> bool:
        try:
            import trafilatura
            return True
        except ImportError:
            return False

    def extract(self, html: str, url: str = "") -> ExtractionResult:
        start = time.perf_counter()
        try:
            import trafilatura

            content = trafilatura.extract(
                html,
                url=url,
                include_links=False,
                include_images=False,
                include_tables=True,
                output_format="txt",
                favor_recall=True,  # Prefer more content over precision
            )

            if content is None:
                content = ""

            word_count = len(content.split())

            return ExtractionResult(
                content=content,
                word_count=word_count,
                duration=time.perf_counter() - start,
                success=word_count >= 50,
            )
        except Exception as exc:
            return ExtractionResult(
                content="",
                word_count=0,
                duration=time.perf_counter() - start,
                success=False,
                error=str(exc),
            )


class ReadabilipyExtractor(ArticleExtractor):
    """ReadabiliPy extractor - Mozilla Readability port."""

    @property
    def name(self) -> str:
        return "readabilipy"

    def is_available(self) -> bool:
        try:
            from readabilipy import simple_json_from_html_string
            return True
        except ImportError:
            return False

    def extract(self, html: str, url: str = "") -> ExtractionResult:
        start = time.perf_counter()
        try:
            from readabilipy import simple_json_from_html_string

            # use_readability=False uses pure Python (no Node.js needed)
            result = simple_json_from_html_string(html, use_readability=False)

            content = result.get("plain_text", "") or ""
            title = result.get("title", "")
            word_count = len(content.split())

            return ExtractionResult(
                content=content,
                word_count=word_count,
                duration=time.perf_counter() - start,
                success=word_count >= 50,
                metadata={"title": title},
            )
        except Exception as exc:
            return ExtractionResult(
                content="",
                word_count=0,
                duration=time.perf_counter() - start,
                success=False,
                error=str(exc),
            )


class Newspaper3kExtractor(ArticleExtractor):
    """Newspaper3k extractor - includes NLP features."""

    @property
    def name(self) -> str:
        return "newspaper3k"

    def is_available(self) -> bool:
        try:
            from newspaper import Article
            return True
        except ImportError:
            return False

    def extract(self, html: str, url: str = "") -> ExtractionResult:
        start = time.perf_counter()
        try:
            from newspaper import Article

            # newspaper3k needs a URL, use placeholder if not provided
            article = Article(url or "http://example.com")
            article.set_html(html)
            article.parse()

            content = article.text or ""
            word_count = len(content.split())

            return ExtractionResult(
                content=content,
                word_count=word_count,
                duration=time.perf_counter() - start,
                success=word_count >= 50,
                metadata={
                    "title": article.title,
                    "authors": article.authors,
                    "publish_date": str(article.publish_date) if article.publish_date else None,
                },
            )
        except Exception as exc:
            return ExtractionResult(
                content="",
                word_count=0,
                duration=time.perf_counter() - start,
                success=False,
                error=str(exc),
            )


def get_all_extractors() -> List[ArticleExtractor]:
    """Return list of all available extractors."""
    all_extractors = [
        ReadabilityLxmlExtractor(),
        TrafilaturaExtractor(),
        ReadabilipyExtractor(),
        Newspaper3kExtractor(),
    ]
    return [e for e in all_extractors if e.is_available()]
