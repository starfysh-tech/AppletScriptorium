"""Helper functions to load test articles from gold standard."""

from pathlib import Path
from typing import List, Dict
import logging

from .gold_standard import GOLD_ANNOTATIONS

logger = logging.getLogger(__name__)


def load_articles_from_directory(articles_dir: Path) -> List[Dict]:
    """Load test articles from a directory of content files.

    Matches gold standard annotations to .content.md files using title matching.

    Args:
        articles_dir: Directory containing *.content.md files

    Returns:
        List of article dicts with url, title, content keys
    """
    if not articles_dir.exists():
        logger.error("Articles directory not found: %s", articles_dir)
        return []

    content_files = list(articles_dir.glob("*.content.md"))
    if not content_files:
        logger.error("No .content.md files found in %s", articles_dir)
        return []

    logger.info("Found %d content files in %s", len(content_files), articles_dir)

    articles = []
    for annotation in GOLD_ANNOTATIONS:
        matched = False

        # Try to match by title (first 20 chars)
        title_prefix = annotation.title.lower()[:20]

        for content_file in content_files:
            content = content_file.read_text(encoding="utf-8")

            # Check if title appears in first 1000 chars of content
            if title_prefix in content.lower()[:1000]:
                article = {
                    "url": annotation.url,
                    "title": annotation.title,
                    "content": content,
                }
                articles.append(article)
                logger.info("Matched: %s -> %s", annotation.title[:40], content_file.name)
                matched = True
                break

        if not matched:
            logger.warning("No content file found for: %s", annotation.title)

    logger.info("Loaded %d/%d articles", len(articles), len(GOLD_ANNOTATIONS))
    return articles


def load_articles_from_runs(runs_dir: Path = None) -> List[Dict]:
    """Load test articles from most recent runs/ directory.

    Args:
        runs_dir: Path to runs directory (defaults to repo root/runs)

    Returns:
        List of article dicts with url, title, content keys
    """
    if runs_dir is None:
        # Find repo root
        current = Path(__file__).resolve()
        repo_root = current.parent.parent.parent
        runs_dir = repo_root / "runs"

    if not runs_dir.exists():
        logger.error("runs/ directory not found at %s", runs_dir)
        return []

    # Find most recent alert directory
    alert_dirs = sorted(runs_dir.glob("alert-*"), reverse=True)
    if not alert_dirs:
        logger.error("No alert-* directories found in %s", runs_dir)
        return []

    most_recent = alert_dirs[0]
    articles_dir = most_recent / "articles"

    logger.info("Using articles from: %s", articles_dir)
    return load_articles_from_directory(articles_dir)


def find_article_by_url(url: str, articles: List[Dict]) -> Dict | None:
    """Find article by URL in loaded articles list.

    Args:
        url: Article URL to find
        articles: List of article dicts

    Returns:
        Article dict if found, None otherwise
    """
    for article in articles:
        if article.get("url") == url:
            return article
    return None


# For manual testing
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        articles_dir = Path(sys.argv[1])
        articles = load_articles_from_directory(articles_dir)
    else:
        articles = load_articles_from_runs()

    print(f"\nLoaded {len(articles)} articles:")
    for i, article in enumerate(articles, 1):
        print(f"  {i}. {article['title'][:60]}")
        print(f"     URL: {article['url']}")
        print(f"     Content length: {len(article['content'])} chars")
