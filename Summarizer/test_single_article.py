#!/usr/bin/env python3
"""Test script to summarize a single article with debug logging enabled."""

import logging
import os
import sys
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from Summarizer.article_fetcher import FetchConfig, fetch_article
from Summarizer.content_cleaner import extract_content
from Summarizer.summarizer import SummarizerConfig, summarize_article

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

def test_article(url: str, model: str = "llama-chat-summary-3.2-3b"):
    """Fetch and summarize a single article with debug output."""

    print(f"\n{'='*80}")
    print(f"Testing article: {url}")
    print(f"Model: {model}")
    print(f"{'='*80}\n")

    # Step 1: Fetch article
    print("Step 1: Fetching article...")
    try:
        fetch_cfg = FetchConfig()
        html_or_markdown = fetch_article(url, fetch_cfg)
        print(f"✓ Fetched {len(html_or_markdown)} bytes")
    except Exception as exc:
        print(f"✗ Fetch failed: {exc}")
        return

    # Step 2: Extract content
    print("\nStep 2: Extracting content...")
    try:
        content = extract_content(html_or_markdown)
        word_count = len(content.split())
        print(f"✓ Extracted {word_count} words")
        print(f"First 200 chars: {content[:200]}...")
    except Exception as exc:
        print(f"✗ Content extraction failed: {exc}")
        return

    # Step 3: Summarize
    print("\nStep 3: Summarizing with LLM...")
    article = {
        "title": "Test Article",
        "url": url,
        "content": content,
    }

    try:
        sum_cfg = SummarizerConfig(model=model)
        summary = summarize_article(article, config=sum_cfg)
        print(f"\n✓ Summary generated successfully!")
        print(f"\nSummary bullets ({len(summary['summary'])}):")
        for i, bullet in enumerate(summary['summary'], 1):
            print(f"  {i}. {bullet.get('text', '')[:100]}...")
    except Exception as exc:
        print(f"\n✗ Summarization failed: {exc}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    # Default to failed medrxiv article
    test_url = "https://www.medrxiv.org/content/10.1101/2025.10.07.25337194v2"

    if len(sys.argv) > 1:
        test_url = sys.argv[1]

    test_article(test_url)
