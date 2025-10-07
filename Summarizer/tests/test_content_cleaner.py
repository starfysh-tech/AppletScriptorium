from __future__ import annotations

from pathlib import Path

from Summarizer.content_cleaner import extract_content


def load_sample(name: str) -> str:
    path = Path('Summarizer/Samples/articles') / name
    return path.read_text(encoding='utf-8')


def test_extract_content_returns_clean_markdown():
    html = load_sample('pro-diction-models.html')
    text = extract_content(html)

    assert "From Prediction to PRO-Diction Models" in text
    assert "Machine-learning risk models" in text
    assert "Start with a narrow cohort" in text


def test_extract_content_strips_navigation():
    html = load_sample('pro-diction-models.html')
    text = extract_content(html)

    assert "Topics" not in text
    assert "Podcasts" not in text
