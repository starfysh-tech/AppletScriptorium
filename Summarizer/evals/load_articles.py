"""Helper functions to load test articles from gold standard."""

import re
from pathlib import Path
from typing import List, Dict
import logging

from .gold_standard import GOLD_ANNOTATIONS

logger = logging.getLogger(__name__)


def _slug(value: str) -> str:
    """Same slug the pipeline uses for article filenames (cli.slugify), first 40 chars."""
    return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()[:40]


def _match_annotations(content_files: List[Path], annotations, *, warn_missing: bool) -> List[Dict]:
    """Match gold annotations to content files.

    The pipeline names each file ``NN-<slug(title)[:40]>.content.md``, so the
    filename is matched against the annotation title's slug. Article bodies
    are not searched: they often omit the title entirely, and a loose text
    match can pick an unrelated article that merely mentions it.
    """
    by_slug = {}
    for f in content_files:
        name = f.name[: -len(".content.md")]
        slug = name.split("-", 1)[1] if re.match(r"^\d+-", name) else name
        by_slug.setdefault(slug, f)  # first (newest) wins

    articles = []
    for annotation in annotations:
        title_slug = _slug(annotation.title)
        if not title_slug:  # an empty key would be meaningless
            logger.warning("Annotation has no title, cannot match content file: %s", annotation.url)
            continue
        # Exact slug first; the file slug is truncated at 40 chars, so fall
        # back to a prefix match only when it is unambiguous.
        match = by_slug.get(title_slug)
        if match is None:
            candidates = [f for slug, f in by_slug.items() if slug.startswith(title_slug) or title_slug.startswith(slug)]
            if len(candidates) > 1:
                logger.warning("Ambiguous content files for %r: %s; skipping", annotation.title[:40], [c.name for c in candidates])
                continue
            match = candidates[0] if candidates else None
        if match is None:
            if warn_missing:
                logger.warning("No content file found for: %s", annotation.title)
            continue
        articles.append({"url": annotation.url, "title": annotation.title, "content": match.read_text(encoding="utf-8", errors="ignore")})
        logger.info("Matched: %s -> %s", annotation.title[:40], match.name)
    return articles


def load_articles_from_directory(articles_dir: Path) -> List[Dict]:
    """Load test articles from a directory of *.content.md files.

    Args:
        articles_dir: Directory containing *.content.md files

    Returns:
        List of article dicts with url, title, content keys
    """
    if not articles_dir.exists():
        logger.error("Articles directory not found: %s", articles_dir)
        return []
    content_files = sorted(articles_dir.glob("*.content.md"))
    if not content_files:
        logger.error("No .content.md files found in %s", articles_dir)
        return []
    logger.info("Found %d content files in %s", len(content_files), articles_dir)
    articles = _match_annotations(content_files, GOLD_ANNOTATIONS, warn_missing=True)
    logger.info("Loaded %d/%d articles", len(articles), len(GOLD_ANNOTATIONS))
    return articles


def load_articles_from_runs(runs_dir: Path = None) -> List[Dict]:
    """Load test articles from the runs/ tree.

    Gold articles come from whichever runs fetched them, so every
    runs/alert-*/articles directory is searched, newest first, and the first
    match per annotation wins.

    Args:
        runs_dir: Path to runs directory (defaults to repo root/runs)

    Returns:
        List of article dicts with url, title, content keys
    """
    if runs_dir is None:
        repo_root = Path(__file__).resolve().parent.parent.parent
        runs_dir = repo_root / "runs"
    if not runs_dir.exists():
        logger.error("runs/ directory not found at %s", runs_dir)
        return []

    alert_dirs = sorted((d for d in runs_dir.glob("alert-*") if (d / "articles").is_dir()), reverse=True)
    content_files = [f for d in alert_dirs for f in sorted((d / "articles").glob("*.content.md"))]
    if not content_files:
        logger.error("No alert-*/articles/*.content.md files found under %s", runs_dir)
        return []

    articles = _match_annotations(content_files, GOLD_ANNOTATIONS, warn_missing=True)
    logger.info("Loaded %d/%d gold articles from %d run directories", len(articles), len(GOLD_ANNOTATIONS), len(alert_dirs))
    return articles


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
