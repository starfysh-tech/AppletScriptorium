"""Categorized test URLs from production logs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal

URLCategory = Literal[
    "js_rendering",
    "insufficient_extraction",
    "paywall",
    "timeout_prone",
    "social_media",
    "baseline_success",
]


@dataclass(frozen=True)
class TestURL:
    """A test URL with metadata for benchmarking."""
    url: str
    domain: str
    category: URLCategory
    notes: str
    expected_min_words: int = 100


# Problematic URLs identified from production logs (runs/summarizer-status.log, workflow.log)
TEST_URLS: List[TestURL] = [
    # === JS Rendering Issues ===
    # These extract wrong content (references section, UI elements) instead of article body
    TestURL(
        url="https://www.nature.com/articles/s41598-025-31255-z",
        domain="nature.com",
        category="js_rendering",
        notes="Extracts references section only, main content is JS-rendered",
        expected_min_words=200,
    ),
    TestURL(
        url="https://www.cureus.com/articles/430477-a-comparative-analysis-of-medial-versus-lateral-unicompartmental-arthroplasty-a-case-matched-analysis-of-patient-reported-outcomes",
        domain="cureus.com",
        category="js_rendering",
        notes="Extracts UI elements (buttons, nav) instead of article content",
        expected_min_words=300,
    ),

    # === Insufficient Extraction ===
    # These return very few words despite having full articles
    TestURL(
        url="https://www.ctvnews.ca/atlantic/nova-scotia/article/nscad-students-revamp-health-care-materials-for-dementia-rehab-patients/",
        domain="ctvnews.ca",
        category="insufficient_extraction",
        notes="Only 7 words extracted with readability-lxml",
        expected_min_words=200,
    ),
    TestURL(
        url="https://firstwordpharma.com/story/6713265",
        domain="firstwordpharma.com",
        category="insufficient_extraction",
        notes="Only 9 words extracted - heavy bot protection",
        expected_min_words=100,
    ),
    TestURL(
        url="https://www.raps.org/news-and-articles/news-articles/2025/11/stakeholders-weigh-in-on-fda-s-draft-clinical-outc",
        domain="raps.org",
        category="insufficient_extraction",
        notes="Only 37 words extracted - restricts bot access",
        expected_min_words=150,
    ),

    # === Paywalls ===
    # No extractor can bypass these - document as known limitation
    TestURL(
        url="https://www.thelancet.com/journals/lanonc/article/PIIS1470-2045(25)00526-1/abstract",
        domain="thelancet.com",
        category="paywall",
        notes="Journal paywall - only abstract accessible",
        expected_min_words=50,  # Lower expectation - paywall
    ),
    TestURL(
        url="https://psychiatryonline.org/doi/10.1176/appi.ps.20250194",
        domain="psychiatryonline.org",
        category="paywall",
        notes="Professional journal paywall",
        expected_min_words=50,
    ),

    # === Timeout Prone ===
    # Very long content that causes LLM timeouts (not extraction issues)
    TestURL(
        url="https://www.openpr.com/news/4300891/medication-adherence-market-outlook-growth-drivers-digital",
        domain="openpr.com",
        category="timeout_prone",
        notes="PR newswire - very long content causes LLM timeout",
        expected_min_words=500,
    ),
    TestURL(
        url="https://www.urotoday.com/conference-highlights/esmo-2025/esmo-2025-bladder-cancer/164142-esmo-2025-the-feasibility-of-wearable-devices-to-assess-patient-reported-outcomes-in-urothelial-cancer-trials-the-discus-substudy.html",
        domain="urotoday.com",
        category="timeout_prone",
        notes="Conference content - very verbose",
        expected_min_words=400,
    ),

    # === Social Media ===
    # Minimal content by design - skip these in production
    TestURL(
        url="https://www.instagram.com/p/DRqArkjiBd7/",
        domain="instagram.com",
        category="social_media",
        notes="Social media post - minimal text content",
        expected_min_words=20,
    ),

    # === Baseline Success ===
    # These work well with current extraction - use for regression testing
    TestURL(
        url="https://pmc.ncbi.nlm.nih.gov/articles/PMC12544051/",
        domain="pmc.ncbi.nlm.nih.gov",
        category="baseline_success",
        notes="PubMed Central - usually extracts well",
        expected_min_words=300,
    ),
    TestURL(
        url="https://pubmed.ncbi.nlm.nih.gov/39631095/",
        domain="pubmed.ncbi.nlm.nih.gov",
        category="baseline_success",
        notes="PubMed abstract - should extract cleanly",
        expected_min_words=100,
    ),
]


def get_urls_by_category(category: URLCategory) -> List[TestURL]:
    """Filter test URLs by category."""
    return [t for t in TEST_URLS if t.category == category]


def get_priority_urls() -> List[TestURL]:
    """Get high-priority URLs for quick testing (js_rendering + insufficient_extraction)."""
    return [t for t in TEST_URLS if t.category in ("js_rendering", "insufficient_extraction")]
