from __future__ import annotations

from pathlib import Path

from content_cleaner import extract_content


def load_sample(name: str) -> str:
    path = Path('Summarizer/Samples/articles') / name
    return path.read_text(encoding='utf-8')


def test_extract_content_basic_structure():
    html = load_sample('pro-diction-models.html')
    blocks = extract_content(html)

    assert blocks[0]["type"] == "heading"
    assert blocks[0]["text"].startswith("From Prediction to PRO-Diction Models")

    paragraphs = [b for b in blocks if b["type"] == "paragraph"]
    assert any("Machine-learning risk models" in p["text"] for p in paragraphs)

    lists = [b for b in blocks if b["type"] == "list"]
    assert len(lists) == 1
    assert "Start with a narrow cohort" in lists[0]["items"][0]


def test_extract_content_strips_navigation():
    html = load_sample('pro-diction-models.html')
    blocks = extract_content(html)
    texts = " ".join(b.get("text", "") for b in blocks if "text" in b)

    assert "Topics" not in texts
    assert "Podcasts" not in texts
