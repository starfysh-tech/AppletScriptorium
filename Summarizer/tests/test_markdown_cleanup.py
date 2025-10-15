from __future__ import annotations

import pytest

from pathlib import Path

from Summarizer.markdown_cleanup import clean_markdown_content, validate_markdown_content


SAMPLES_DIR = Path(__file__).resolve().parent.parent / "Samples"


def test_clean_markdown_removes_contact_blocks():
    raw = (
        "# Article Title\n\n"
        "Body paragraph.\n\n"
        "* [+233 244 300 000](tel:+233244300000)\n"
        "* Contact our support team\n"
    )
    cleaned, removed = clean_markdown_content(raw)
    assert "+233" not in cleaned
    assert "support team" not in cleaned
    assert "Article Title" in cleaned
    assert any("+233" in entry for entry in removed)


def test_clean_markdown_removes_more_sections():
    raw = (
        "# Main Article\n\n"
        "Content here.\n\n"
        "## More MTN Ghana News\n"
        "* Link 1\n"
        "* Link 2\n"
    )
    cleaned, removed = clean_markdown_content(raw)
    assert "## More MTN Ghana News" not in cleaned
    assert "Content here." in cleaned
    assert any("More MTN" in entry for entry in removed)


def test_clean_markdown_preserves_valid_content():
    raw = (
        "# Study Finds More Exercise Helps Recovery\n\n"
        "Patients who exercised more showed better outcomes.\n\n"
        "## Methods\n"
        "Details here.\n"
    )
    cleaned, removed = clean_markdown_content(raw)
    assert "Study Finds" in cleaned
    assert "## Methods" in cleaned
    assert removed == []


def test_clean_markdown_normalizes_whitespace():
    raw = "Line 1\n\n\n\nLine 2\n\n\nLine 3"
    cleaned, _ = clean_markdown_content(raw)
    assert "\n\n\n" not in cleaned


def test_validate_markdown_empty():
    warnings = validate_markdown_content("")
    assert "empty" in warnings


def test_validate_markdown_short():
    warnings = validate_markdown_content("Short body")
    assert any("short" in w.lower() for w in warnings)


def test_validate_markdown_no_paragraphs():
    warnings = validate_markdown_content("Single line content here")
    assert any("paragraph" in w.lower() for w in warnings)


def test_validate_markdown_valid():
    content = (
        "# Title\n\n"
        "Paragraph one with sufficient content to exceed the minimum threshold.\n\n"
        "Paragraph two continues the narrative with additional detail.\n\n"
        "Paragraph three wraps up the article.\n"
    )
    warnings = validate_markdown_content(content)
    assert warnings == []


@pytest.mark.skipif(
    not (SAMPLES_DIR / "businessghana-mtn-girls-code.fallback.md").exists(),
    reason="Sample fixture missing",
)
def test_clean_markdown_fixture_regression():
    raw = (SAMPLES_DIR / "businessghana-mtn-girls-code.fallback.md").read_text(encoding="utf-8")
    expected = (SAMPLES_DIR / "businessghana-mtn-girls-code.cleaned.md").read_text(encoding="utf-8")

    cleaned, removed = clean_markdown_content(raw)

    assert cleaned.strip() == expected.strip()
    assert any("More" in entry for entry in removed)
