"""Quality metrics for extraction evaluation.

Uses shared indicators from quality_checks.py to stay in sync with production code.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..quality_checks import (
    PAYWALL_INDICATORS,
    UI_INDICATORS,
    REFERENCE_PATTERN,
)


@dataclass(frozen=True)
class QualityMetrics:
    """Quality assessment of extracted content."""
    word_count: int
    is_paywall: bool
    is_ui_elements: bool
    is_references_only: bool
    paragraph_count: int

    @property
    def is_valid(self) -> bool:
        """Content passes all quality checks."""
        return (
            self.word_count >= 100
            and not self.is_paywall
            and not self.is_ui_elements
            and not self.is_references_only
        )

    @property
    def quality_score(self) -> float:
        """Composite quality score (0.0 - 1.0).

        Scoring:
        - Base: word_count normalized (100 words = 0.5, 500+ words = 1.0)
        - Penalties: -0.5 for each quality failure
        """
        if self.word_count == 0:
            return 0.0

        # Base score from word count (0.0 - 1.0)
        base = min(1.0, self.word_count / 500)

        # Penalties for quality failures
        penalties = 0.0
        if self.is_paywall:
            penalties += 0.5
        if self.is_ui_elements:
            penalties += 0.5
        if self.is_references_only:
            penalties += 0.5

        return max(0.0, base - penalties)


def evaluate_quality(content: str) -> QualityMetrics:
    """Evaluate extraction quality using shared indicators from quality_checks.py."""
    if not content or not content.strip():
        return QualityMetrics(
            word_count=0,
            is_paywall=False,
            is_ui_elements=False,
            is_references_only=False,
            paragraph_count=0,
        )

    lines = content.strip().splitlines()
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    word_count = len(content.split())
    paragraph_count = len([line for line in non_empty_lines if len(line) > 50])

    # Paywall detection using shared indicators
    content_lower = content.lower()
    paywall_count = sum(1 for ind in PAYWALL_INDICATORS if ind.lower() in content_lower)
    is_paywall = paywall_count >= 2

    # UI element detection using shared indicators
    ui_count = sum(1 for ind in UI_INDICATORS if ind in content)
    is_ui_elements = ui_count >= 2

    # References-only detection using shared pattern
    reference_lines = sum(1 for line in non_empty_lines if REFERENCE_PATTERN.match(line))
    is_references_only = (
        len(non_empty_lines) > 10 and reference_lines / len(non_empty_lines) > 0.7
    )

    return QualityMetrics(
        word_count=word_count,
        is_paywall=is_paywall,
        is_ui_elements=is_ui_elements,
        is_references_only=is_references_only,
        paragraph_count=paragraph_count,
    )
