"""Utilities for cleaning and validating Markdown fallback content."""
from __future__ import annotations

import re
from typing import Iterable, Tuple, List


# Patterns that mark the beginning of navigation or contact sections we want to drop.
_SECTION_PATTERNS: Iterable[re.Pattern[str]] = (
    re.compile(r"^\s*\*\s+\[\+?\d"),  # Telephone / contact bullet
    re.compile(r"^\s*##\s+more\b", re.IGNORECASE),  # "## More ..." headings
)


def clean_markdown_content(markdown: str) -> Tuple[str, List[str]]:
    """Strip navigation/footer clutter from Markdown.

    Returns (cleaned_markdown, removed_section_labels).
    """
    lines = markdown.splitlines()
    cleaned: List[str] = []
    removed_sections: List[str] = []

    skip_section = False
    for line in lines:
        stripped = line.strip()
        if stripped == "":
            skip_section = False
            cleaned.append("")
            continue

        matched_pattern = None
        for pattern in _SECTION_PATTERNS:
            if pattern.match(line):
                matched_pattern = pattern
                break

        if matched_pattern:
            removed_sections.append(stripped)
            skip_section = True
            continue

        if skip_section:
            # Continue skipping lines within the removed section until a blank line resets it.
            removed_sections.append(stripped)
            continue

        cleaned.append(line.rstrip())

    # Collapse multiple blank lines into maximum one blank line.
    normalized: List[str] = []
    blank_streak = 0
    for line in cleaned:
        if line.strip() == "":
            blank_streak += 1
        else:
            blank_streak = 0
        if blank_streak < 2:
            normalized.append(line)

    # Trim leading/trailing blank lines.
    while normalized and normalized[0].strip() == "":
        normalized.pop(0)
    while normalized and normalized[-1].strip() == "":
        normalized.pop()

    return "\n".join(normalized), removed_sections


def validate_markdown_content(markdown: str) -> List[str]:
    """Return a list of warnings describing potential quality issues."""
    warnings: List[str] = []

    stripped = markdown.strip()
    if not stripped:
        warnings.append("empty")

    if len(stripped) < 100:
        warnings.append(f"short ({len(stripped)} chars)")

    if stripped.count("\n") < 3:
        warnings.append("no paragraphs")

    return warnings


__all__ = ["clean_markdown_content", "validate_markdown_content"]
