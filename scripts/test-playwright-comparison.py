#!/usr/bin/env python3
"""Compare current Playwright approach with Jina AI."""
import time
from pathlib import Path

from Summarizer.article_fetcher import fetch_article, FetchConfig, clear_cache
from Summarizer.content_cleaner import extract_content

# Use news10.com since it requires headed mode currently
TEST_URL = "https://www.news10.com/news/local-news/"


def main():
    print("=== Playwright vs Jina AI Comparison ===\n")
    print(f"Testing: {TEST_URL}\n")

    # Clear cache to force fresh fetch
    clear_cache()

    print("Fetching with current Playwright approach...")
    print("-" * 80)
    start = time.time()
    try:
        html = fetch_article(TEST_URL, FetchConfig())
        elapsed = time.time() - start
        print(f"✓ SUCCESS in {elapsed:.2f}s")
        print(f"  Raw HTML length: {len(html):,} chars")

        # Clean to Markdown
        markdown = extract_content(html)
        print(f"  Cleaned Markdown length: {len(markdown):,} chars")
        print(f"\n  First 500 chars of Markdown:")
        print(f"  {markdown[:500]}")

        Path("/tmp/playwright-test.md").write_text(markdown, encoding="utf-8")
        print(f"\n  Full Markdown saved to: /tmp/playwright-test.md")

    except Exception as e:
        elapsed = time.time() - start
        print(f"✗ FAILED in {elapsed:.2f}s")
        print(f"  Error: {e}")

    print("\n" + "=" * 80)
    print("\nTo compare:")
    print("  Jina AI:     /tmp/jina-test-3.txt")
    print("  Playwright:  /tmp/playwright-test.md")


if __name__ == "__main__":
    main()
