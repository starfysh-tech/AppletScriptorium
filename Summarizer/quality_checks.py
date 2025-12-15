"""Shared quality validation logic for content extraction.

This module centralizes quality indicators and checks used by both
content_cleaner.py (during extraction) and cli.py (during pipeline validation).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Indicators that content is behind a Cloudflare protection challenge
CLOUDFLARE_INDICATORS = [
    'Just a moment',
    'checking your browser',
    'Cloudflare',
    'Ray ID',
    'enable JavaScript',
    'challenge passed',
]

# Indicators that content is behind a paywall
PAYWALL_INDICATORS = [
    'Get Access',
    'Purchase this article',
    'Get Institutional Access',
    'full access to this article',
    'subscription options',
    'Already a subscriber',
    'purchase options',
]

# Indicators that extracted content is UI elements, not article content
UI_INDICATORS = [
    'Please choose',
    'Sign in',
    'Register',
    'Subscribe',
    'Select your specialty',
    "I'm not a medical professional",
    'Log in to continue',
    'Create account',
    # Promotional/advertising indicators (for sites like cureus.com)
    'Why publish in',
    'Click below to find out',
    'Sponsored by',
]

# Pattern for detecting reference/citation lines
REFERENCE_PATTERN = re.compile(r'^\d+\.\s+[A-Z][a-z]+,?\s+[A-Z]')


@dataclass(frozen=True)
class QualityResult:
    """Result of a quality check."""
    is_failure: bool
    reason: str = ""


def check_content_quality(content: str) -> QualityResult:
    """Check if extracted content is valid article content.

    Returns QualityResult indicating if content fails quality checks
    and the reason for failure.

    Checks for:
    - Paywall indicators (2+ matches = failure)
    - UI element indicators (2+ matches = failure)
    - References-only content (>70% reference lines = failure)
    """
    if not content or not content.strip():
        return QualityResult(is_failure=True, reason="empty content")

    lines = content.split('\n')
    non_empty_lines = [line.strip() for line in lines if line.strip()]

    if not non_empty_lines:
        return QualityResult(is_failure=True, reason="empty content")

    content_lower = content.lower()

    # Check for Cloudflare protection challenge
    cloudflare_count = sum(
        1 for ind in CLOUDFLARE_INDICATORS
        if ind.lower() in content_lower
    )
    if cloudflare_count >= 2:
        return QualityResult(is_failure=True, reason="Cloudflare protection blocked content access")

    # Check for paywall indicators
    paywall_count = sum(
        1 for ind in PAYWALL_INDICATORS
        if ind.lower() in content_lower
    )
    if paywall_count >= 2:
        return QualityResult(is_failure=True, reason="content behind paywall")

    # Check for UI element indicators
    ui_count = sum(1 for ind in UI_INDICATORS if ind in content)
    if ui_count >= 2:
        return QualityResult(is_failure=True, reason="content appears to be UI elements")

    # Check for references-only content
    if len(non_empty_lines) > 10:
        reference_lines = sum(
            1 for line in non_empty_lines
            if REFERENCE_PATTERN.match(line)
        )
        if reference_lines / len(non_empty_lines) > 0.7:
            return QualityResult(
                is_failure=True,
                reason="content appears to be references section only"
            )

    return QualityResult(is_failure=False)


def is_low_quality(content: str) -> bool:
    """Quick check if content fails quality validation.

    Convenience wrapper around check_content_quality() for simple boolean checks.
    """
    return check_content_quality(content).is_failure
