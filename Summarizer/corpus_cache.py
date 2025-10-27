"""Save and load article corpus to/from disk.

Provides functions to persist article collections with their content and metadata,
enabling reprocessing without re-fetching articles.

Usage example:

    from pathlib import Path
    from Summarizer.corpus_cache import save_corpus, load_corpus, iter_corpus

    # Save articles after fetching
    articles = [
        {
            "title": "Article Title",
            "url": "https://example.com",
            "publisher": "Publisher",
            "snippet": "Article snippet",
            "content": "# Article Title\n\nCleaned markdown content...",
            "raw_html": "<html>...</html>"  # Optional
        }
    ]
    metadata = save_corpus(Path("runs/run-001"), "alert.eml", articles)

    # Load corpus for reprocessing
    corpus_dir = Path("runs/run-001/corpus")
    metadata, cached_articles = load_corpus(corpus_dir)

    # Iterate articles for summarization
    from Summarizer.summarizer import summarize_article
    for article in iter_corpus(corpus_dir):
        summary = summarize_article(article)  # article dict has all required keys
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List


@dataclass
class CorpusMetadata:
    """Metadata about a saved corpus."""
    source_eml: str  # Original .eml filename
    timestamp: str  # ISO 8601
    article_count: int
    corpus_hash: str  # SHA256 of articles.json for validation


@dataclass
class CachedArticle:
    """Reference to a cached article with file paths."""
    index: int
    title: str
    url: str
    publisher: str
    snippet: str
    content_path: str  # article-NNN.content.md (relative to corpus dir)
    source_html_path: str  # article-NNN.source.html


def save_corpus(output_dir: Path, source_eml: str, articles: List[Dict]) -> CorpusMetadata:
    """Save article corpus to disk.

    Creates corpus/ subdirectory with metadata, article index, and content files.

    Args:
        output_dir: Directory to create corpus/ subdirectory in
        source_eml: Name of source .eml file
        articles: List of article dicts with keys: title, url, publisher, snippet, content, raw_html

    Returns:
        CorpusMetadata with timestamp and integrity hash

    Example:
        >>> articles = [
        ...     {
        ...         "title": "Test Article",
        ...         "url": "https://example.com",
        ...         "publisher": "Example",
        ...         "snippet": "Test snippet",
        ...         "content": "# Test\\n\\nArticle content",
        ...         "raw_html": "<html>...</html>"
        ...     }
        ... ]
        >>> metadata = save_corpus(Path("/tmp/test"), "alert.eml", articles)
        >>> metadata.article_count
        1
    """
    corpus_dir = output_dir / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)

    # Build cached article index
    cached_articles = []
    for idx, article in enumerate(articles):
        # Generate padded index for sorting (000, 001, ...)
        padded_idx = f"{idx:03d}"
        content_rel = f"article-{padded_idx}.content.md"
        html_rel = f"article-{padded_idx}.source.html"

        cached_articles.append({
            "index": idx,
            "title": article.get("title", ""),
            "url": article.get("url", ""),
            "publisher": article.get("publisher", ""),
            "snippet": article.get("snippet", ""),
            "content_path": content_rel,
            "source_html_path": html_rel,
        })

        # Write content files
        content = article.get("content", "")
        (corpus_dir / content_rel).write_text(content, encoding="utf-8")

        raw_html = article.get("raw_html", "")
        if raw_html:
            (corpus_dir / html_rel).write_text(raw_html, encoding="utf-8")
        else:
            # Write empty file if no HTML available
            (corpus_dir / html_rel).write_text("", encoding="utf-8")

    # Write articles.json
    articles_json_path = corpus_dir / "articles.json"
    articles_json = json.dumps(cached_articles, indent=2) + "\n"
    articles_json_path.write_text(articles_json, encoding="utf-8")

    # Calculate hash for integrity checking
    corpus_hash = hashlib.sha256(articles_json.encode("utf-8")).hexdigest()

    # Write metadata
    timestamp = datetime.now(timezone.utc).isoformat()
    metadata = CorpusMetadata(
        source_eml=source_eml,
        timestamp=timestamp,
        article_count=len(articles),
        corpus_hash=corpus_hash,
    )
    metadata_path = corpus_dir / "metadata.json"
    metadata_path.write_text(json.dumps(asdict(metadata), indent=2) + "\n", encoding="utf-8")

    logging.info(f"[corpus] Saved {len(articles)} articles to {corpus_dir}")
    return metadata


def load_corpus(corpus_dir: Path) -> tuple[CorpusMetadata, List[CachedArticle]]:
    """Load corpus metadata and article index from disk.

    Validates integrity using SHA256 hash stored in metadata.

    Args:
        corpus_dir: Path to corpus/ directory

    Returns:
        Tuple of (CorpusMetadata, list of CachedArticle objects)

    Raises:
        ValueError: If required files missing or hash validation fails

    Example:
        >>> metadata, articles = load_corpus(Path("/tmp/test/corpus"))
        >>> len(articles)
        1
    """
    metadata_path = corpus_dir / "metadata.json"
    articles_path = corpus_dir / "articles.json"

    if not metadata_path.exists():
        raise ValueError(f"Missing metadata.json in {corpus_dir}")
    if not articles_path.exists():
        raise ValueError(f"Missing articles.json in {corpus_dir}")

    # Load and parse files
    metadata_dict = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata = CorpusMetadata(**metadata_dict)

    articles_json = articles_path.read_text(encoding="utf-8")
    articles_data = json.loads(articles_json)

    # Validate hash
    computed_hash = hashlib.sha256(articles_json.encode("utf-8")).hexdigest()
    if computed_hash != metadata.corpus_hash:
        raise ValueError(
            f"Corpus integrity check failed: expected {metadata.corpus_hash}, "
            f"got {computed_hash}"
        )

    # Convert to CachedArticle objects
    cached_articles = [CachedArticle(**article) for article in articles_data]

    logging.info(f"[corpus] Loaded {len(cached_articles)} articles from {corpus_dir}")
    return metadata, cached_articles


def iter_corpus(corpus_dir: Path) -> Iterator[Dict]:
    """Iterate over corpus articles in format compatible with summarize_article().

    Yields article dicts with content loaded from .content.md files.
    Skips articles with missing content files (logs warning).

    Args:
        corpus_dir: Path to corpus/ directory

    Yields:
        Article dicts with keys: title, url, publisher, snippet, content

    Example:
        >>> for article in iter_corpus(Path("/tmp/test/corpus")):
        ...     print(article["title"])
        Test Article
    """
    _, cached_articles = load_corpus(corpus_dir)

    for cached in cached_articles:
        content_path = corpus_dir / cached.content_path

        if not content_path.exists():
            logging.warning(
                f"[corpus] Skipping article {cached.index}: missing content file {content_path}"
            )
            continue

        content = content_path.read_text(encoding="utf-8")

        yield {
            "title": cached.title,
            "url": cached.url,
            "publisher": cached.publisher,
            "snippet": cached.snippet,
            "content": content,
        }


__all__ = [
    "CorpusMetadata",
    "CachedArticle",
    "save_corpus",
    "load_corpus",
    "iter_corpus",
]
