"""Tests for corpus_cache module."""
import json
from pathlib import Path

import pytest

from Summarizer.corpus_cache import (
    CachedArticle,
    CorpusMetadata,
    iter_corpus,
    load_corpus,
    save_corpus,
)


@pytest.fixture
def sample_articles():
    """Sample articles for testing."""
    return [
        {
            "title": "First Article",
            "url": "https://example.com/first",
            "publisher": "Example Publisher",
            "snippet": "First article snippet",
            "content": "# First Article\n\nContent goes here.",
            "raw_html": "<html><body>First article HTML</body></html>",
        },
        {
            "title": "Second Article",
            "url": "https://example.com/second",
            "publisher": "Another Publisher",
            "snippet": "Second article snippet",
            "content": "# Second Article\n\nMore content.",
            "raw_html": "<html><body>Second article HTML</body></html>",
        },
    ]


def test_save_corpus(tmp_path, sample_articles):
    """Test saving corpus to disk."""
    metadata = save_corpus(tmp_path, "test-alert.eml", sample_articles)

    # Check metadata
    assert metadata.source_eml == "test-alert.eml"
    assert metadata.article_count == 2
    assert len(metadata.corpus_hash) == 64  # SHA256 hex digest

    # Check directory structure
    corpus_dir = tmp_path / "corpus"
    assert corpus_dir.exists()
    assert (corpus_dir / "metadata.json").exists()
    assert (corpus_dir / "articles.json").exists()
    assert (corpus_dir / "article-000.content.md").exists()
    assert (corpus_dir / "article-000.source.html").exists()
    assert (corpus_dir / "article-001.content.md").exists()
    assert (corpus_dir / "article-001.source.html").exists()


def test_load_corpus(tmp_path, sample_articles):
    """Test loading corpus from disk."""
    save_corpus(tmp_path, "test-alert.eml", sample_articles)
    corpus_dir = tmp_path / "corpus"

    metadata, articles = load_corpus(corpus_dir)

    # Check metadata
    assert metadata.source_eml == "test-alert.eml"
    assert metadata.article_count == 2

    # Check articles
    assert len(articles) == 2
    assert isinstance(articles[0], CachedArticle)
    assert articles[0].title == "First Article"
    assert articles[0].url == "https://example.com/first"
    assert articles[0].content_path == "article-000.content.md"
    assert articles[1].title == "Second Article"


def test_roundtrip_save_load(tmp_path, sample_articles):
    """Test save followed by load preserves data."""
    save_metadata = save_corpus(tmp_path, "test-alert.eml", sample_articles)
    load_metadata, articles = load_corpus(tmp_path / "corpus")

    # Metadata should match
    assert save_metadata.source_eml == load_metadata.source_eml
    assert save_metadata.article_count == load_metadata.article_count
    assert save_metadata.corpus_hash == load_metadata.corpus_hash

    # Articles should match
    assert len(articles) == len(sample_articles)
    for cached, original in zip(articles, sample_articles):
        assert cached.title == original["title"]
        assert cached.url == original["url"]
        assert cached.publisher == original["publisher"]
        assert cached.snippet == original["snippet"]


def test_load_corpus_validates_hash(tmp_path, sample_articles):
    """Test that load_corpus detects corrupted articles.json."""
    save_corpus(tmp_path, "test-alert.eml", sample_articles)
    corpus_dir = tmp_path / "corpus"

    # Corrupt articles.json
    articles_path = corpus_dir / "articles.json"
    data = json.loads(articles_path.read_text())
    data[0]["title"] = "CORRUPTED"
    articles_path.write_text(json.dumps(data, indent=2) + "\n")

    # Load should fail with hash mismatch
    with pytest.raises(ValueError, match="integrity check failed"):
        load_corpus(corpus_dir)


def test_load_corpus_missing_files(tmp_path):
    """Test that load_corpus raises ValueError for missing files."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()

    with pytest.raises(ValueError, match="Missing metadata.json"):
        load_corpus(corpus_dir)

    # Create metadata but not articles
    metadata = {
        "source_eml": "test.eml",
        "timestamp": "2025-01-01T00:00:00+00:00",
        "article_count": 0,
        "corpus_hash": "abc123",
    }
    (corpus_dir / "metadata.json").write_text(json.dumps(metadata))

    with pytest.raises(ValueError, match="Missing articles.json"):
        load_corpus(corpus_dir)


def test_iter_corpus(tmp_path, sample_articles):
    """Test iterating over corpus articles."""
    save_corpus(tmp_path, "test-alert.eml", sample_articles)
    corpus_dir = tmp_path / "corpus"

    articles_list = list(iter_corpus(corpus_dir))

    # Check count
    assert len(articles_list) == 2

    # Check format matches summarize_article() expectations
    article = articles_list[0]
    assert set(article.keys()) == {"title", "url", "publisher", "snippet", "content"}
    assert article["title"] == "First Article"
    assert article["url"] == "https://example.com/first"
    assert article["content"].startswith("# First Article")

    # Check second article
    article2 = articles_list[1]
    assert article2["title"] == "Second Article"


def test_iter_corpus_missing_content(tmp_path, sample_articles, caplog):
    """Test that iter_corpus skips articles with missing content files."""
    save_corpus(tmp_path, "test-alert.eml", sample_articles)
    corpus_dir = tmp_path / "corpus"

    # Delete one content file
    (corpus_dir / "article-001.content.md").unlink()

    articles_list = list(iter_corpus(corpus_dir))

    # Should only yield first article
    assert len(articles_list) == 1
    assert articles_list[0]["title"] == "First Article"

    # Should log warning
    assert "Skipping article 1" in caplog.text
    assert "missing content file" in caplog.text


def test_save_corpus_handles_missing_html(tmp_path):
    """Test that save_corpus handles articles without raw_html."""
    articles = [
        {
            "title": "No HTML Article",
            "url": "https://example.com/nohtml",
            "publisher": "Publisher",
            "snippet": "Snippet",
            "content": "# Content\n\nOnly markdown.",
            # No raw_html key
        }
    ]

    save_corpus(tmp_path, "test.eml", articles)
    corpus_dir = tmp_path / "corpus"

    # HTML file should exist but be empty
    html_path = corpus_dir / "article-000.source.html"
    assert html_path.exists()
    assert html_path.read_text() == ""


def test_save_corpus_creates_directories(tmp_path):
    """Test that save_corpus creates missing directories."""
    output_dir = tmp_path / "nested" / "path"
    articles = [
        {
            "title": "Test",
            "url": "https://example.com",
            "publisher": "Pub",
            "snippet": "Snip",
            "content": "Content",
            "raw_html": "<html></html>",
        }
    ]

    save_corpus(output_dir, "test.eml", articles)

    assert (output_dir / "corpus" / "metadata.json").exists()
