"""CLI entry point for extraction benchmark.

Usage:
    python3 -m Summarizer.extraction_benchmark
    python3 -m Summarizer.extraction_benchmark --urls js_rendering
    python3 -m Summarizer.extraction_benchmark --extractors trafilatura,readability-lxml
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from . import (
    ExtractionBenchmark,
    generate_markdown_report,
    get_all_extractors,
    TEST_URLS,
    get_urls_by_category,
    get_priority_urls,
)


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark article extraction libraries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run full benchmark
    python3 -m Summarizer.extraction_benchmark

    # Test only JS rendering URLs
    python3 -m Summarizer.extraction_benchmark --urls js_rendering

    # Test only priority URLs (js_rendering + insufficient_extraction)
    python3 -m Summarizer.extraction_benchmark --urls priority

    # Test specific extractors
    python3 -m Summarizer.extraction_benchmark --extractors trafilatura,readability-lxml
        """,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: runs/extraction-benchmark-TIMESTAMP)",
    )
    parser.add_argument(
        "--urls",
        type=str,
        default="all",
        help="URL category: all, priority, js_rendering, insufficient_extraction, paywall, etc.",
    )
    parser.add_argument(
        "--extractors",
        type=str,
        default=None,
        help="Comma-separated list of extractors to test (default: all available)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Output directory
    if args.output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        args.output_dir = Path(f"runs/extraction-benchmark-{timestamp}")

    # Select URLs
    if args.urls == "all":
        test_urls = TEST_URLS
    elif args.urls == "priority":
        test_urls = get_priority_urls()
    else:
        test_urls = get_urls_by_category(args.urls)
        if not test_urls:
            print(f"Error: No URLs found for category '{args.urls}'", file=sys.stderr)
            print("Available categories: all, priority, js_rendering, insufficient_extraction, paywall, timeout_prone, social_media, baseline_success")
            sys.exit(1)

    # Select extractors
    all_extractors = get_all_extractors()
    if args.extractors:
        names = [n.strip() for n in args.extractors.split(",")]
        extractors = [e for e in all_extractors if e.name in names]
        if not extractors:
            print(f"Error: No matching extractors found for '{args.extractors}'", file=sys.stderr)
            print(f"Available extractors: {', '.join(e.name for e in all_extractors)}")
            sys.exit(1)
    else:
        extractors = all_extractors

    # Print config
    print(f"Output directory: {args.output_dir}")
    print(f"Extractors: {', '.join(e.name for e in extractors)}")
    print(f"Test URLs: {len(test_urls)} ({args.urls})")
    print()

    # Run benchmark
    benchmark = ExtractionBenchmark(
        output_dir=args.output_dir,
        extractors=extractors,
        test_urls=test_urls,
    )
    results = benchmark.run_benchmark()

    # Generate report
    report_path = args.output_dir / "report.md"
    report = generate_markdown_report(results, report_path)

    print()
    print("=" * 60)
    print(report)
    print("=" * 60)
    print(f"\nReport saved to: {report_path}")
    print(f"Raw results: {args.output_dir / 'results.json'}")


if __name__ == "__main__":
    main()
