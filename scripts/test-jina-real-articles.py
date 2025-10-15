#!/usr/bin/env python3
"""Test Jina AI with actual article URLs from problematic domains."""
import time
from pathlib import Path

import requests

# Real article URLs from CRAWLEE_DOMAINS (from fixture)
TEST_URLS = [
    "https://dailynews.ascopubs.org/do/prediction-pro-diction-models-incorporating-patient-reported-outcomes-into-predictive",
    "https://www.urotoday.com/recent-abstracts/pelvic-health-reconstruction/pelvic-prolapse/163406-patient-reported-outcome-measures-used-to-assess-surgical-interventions-for-pelvic-organ-prolapse-stress-urinary-incontinence-and-mesh-complications-a-scoping-review-for-the-development-of-the-appraise-prom.html",
    "https://pmc.ncbi.nlm.nih.gov/articles/PMC12475716/",
    "https://obgyn.onlinelibrary.wiley.com/doi/10.1111/1471-0528.18355",
    "https://www.sciencedirect.com/science/article/abs/pii/S0883540325012227",
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
            "first_1000_chars": content[:1000],
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
    print("=== Jina AI Real Article Test ===\n")

    results = []
    for i, url in enumerate(TEST_URLS, 1):
        domain = url.split("/")[2]
        print(f"\n[{i}/{len(TEST_URLS)}] {domain}")
        print("-" * 80)

        result = fetch_with_jina(url)
        results.append((domain, url, result))

        if result["success"]:
            print(f"✓ SUCCESS in {result['elapsed']:.2f}s")
            print(f"  Content length: {result['content_length']:,} chars")
            print(f"\n  First 1000 chars:")
            print(f"  {result['first_1000_chars']}")

            # Save full content
            filename = f"/tmp/jina-article-{i}.txt"
            Path(filename).write_text(result["content"], encoding="utf-8")
            print(f"\n  Saved: {filename}")
        else:
            print(f"✗ FAILED in {result['elapsed']:.2f}s")
            print(f"  Error: {result['error']}")

    # Summary
    print("\n" + "=" * 80)
    print("\nSUMMARY:")
    successes = sum(1 for _, _, r in results if r["success"])
    print(f"  {successes}/{len(results)} successful")

    if successes > 0:
        avg_time = sum(r["elapsed"] for _, _, r in results if r["success"]) / successes
        avg_length = sum(r["content_length"] for _, _, r in results if r["success"]) / successes
        print(f"  Average time: {avg_time:.2f}s")
        print(f"  Average length: {avg_length:,.0f} chars")


if __name__ == "__main__":
    main()
