from __future__ import annotations

from pathlib import Path

from Summarizer.digest_renderer import render_digest_html, render_digest_text

SAMPLE_SUMMARY = {
    "title": "From Prediction to PRO-Diction Models",
    "url": "https://example.com/article",
    "publisher": "ASCO Daily News",
    "snippet": "AI models need patient input to work",
    "summary": [
        {"type": "bullet", "text": "bullet 1"},
        {"type": "bullet", "text": "bullet 2"},
        {"type": "bullet", "text": "bullet 3"},
    ],
}


def test_render_digest_html(tmp_path: Path):
    html_output = render_digest_html([SAMPLE_SUMMARY])
    assert "PRO Alert Digest" in html_output
    assert "ASCO Daily News" in html_output
    # Executive summary adds 1 bullet, plus 3 article bullets = 4 total
    assert html_output.count("<li>bullet") == 4


def test_render_digest_text():
    text_output = render_digest_text([SAMPLE_SUMMARY])
    lines = text_output.splitlines()
    assert lines[0].startswith("PRO Alert Digest —")
    assert any("bullet 1" in line for line in lines)
    assert "ASCO Daily News" in text_output


def test_render_digest_missing_section():
    missing = [{"url": "https://blocked.example", "reason": "HTTP 403"}]
    text_output = render_digest_text([SAMPLE_SUMMARY], missing=missing)
    assert "Missing articles" in text_output
    assert "- https://blocked.example — HTTP 403" in text_output

    html_output = render_digest_html([SAMPLE_SUMMARY], missing=missing)
    assert "Missing articles" in html_output
    assert "https://blocked.example" in html_output
