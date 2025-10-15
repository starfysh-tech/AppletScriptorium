#!/usr/bin/env python3
"""Quick feasibility test for Jina AI Reader API as Playwright replacement."""
import time
from pathlib import Path

import requests

# Test URLs from problematic domains
TEST_URLS = [
    "https://www.urotoday.com/recent-abstracts/urologic-oncology",
    "https://www.medrxiv.org/content/10.1101/2024.01.15.24301234v1",
    "https://www.news10.com/news/local-news/",
]

JINA_API_KEY = "jina_b9b85c66b63641cb974c3c536eca329bc13ojUPAu2R-_c6PIwITUqFW6EXu"


def fetch_with_jina(url: str) -> dict:
    """Fetch URL via Jina AI Reader API."""
    start = time.time()
    try:
        response = requests.get(
            f"https://r.jina.ai/{url}",
            headers={"Authorization": f"Bearer {JINA_API_KEY}"},
            timeout=30,
        )
        elapsed = time.time() - start
        response.raise_for_status()

        content = response.text
        return {
            "success": True,
            "elapsed": elapsed,
            "content_length": len(content),
            "first_500_chars": content[:500],
            "content": content,
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "success": False,
            "elapsed": elapsed,
            "error": str(e),
        }


def main():
    print("=== Jina AI Reader API Feasibility Test ===\n")

    for i, url in enumerate(TEST_URLS, 1):
        print(f"\n[{i}/{len(TEST_URLS)}] Testing: {url}")
        print("-" * 80)

        result = fetch_with_jina(url)

        if result["success"]:
            print(f"✓ SUCCESS in {result['elapsed']:.2f}s")
            print(f"  Content length: {result['content_length']:,} chars")
            print(f"\n  First 500 chars:")
            print(f"  {result['first_500_chars'][:500]}")

            # Save full content for inspection
            filename = f"/tmp/jina-test-{i}.txt"
            Path(filename).write_text(result["content"], encoding="utf-8")
            print(f"\n  Full content saved to: {filename}")
        else:
            print(f"✗ FAILED in {result['elapsed']:.2f}s")
            print(f"  Error: {result['error']}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
