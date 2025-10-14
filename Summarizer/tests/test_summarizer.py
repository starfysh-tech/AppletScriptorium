from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from Summarizer.content_cleaner import extract_content
from Summarizer.summarizer import SummarizerConfig, SummarizerError, summarize_article


@pytest.fixture(scope="module")
def sample_article() -> dict[str, Any]:
    html = Path('Summarizer/Samples/articles/pro-diction-models.html').read_text(encoding='utf-8')
    content = extract_content(html)
    assert isinstance(content, str)
    return {
        "title": "From Prediction to PRO-Diction Models",
        "url": "https://example.com/article",
        "content": content,
    }


def test_summarizer_uses_runner(sample_article):
    def fake_runner(prompt: str, cfg: SummarizerConfig) -> str:
        assert cfg.model == "qwen3:latest"
        assert "Title:" in prompt
        assert "Machine-learning risk models" in prompt
        return "- Bullet one\n- Bullet two\n- Bullet three"

    result = summarize_article(sample_article, config=SummarizerConfig(model="qwen3:latest"), runner=fake_runner)
    assert result["summary"] == [
        {"type": "bullet", "text": "Bullet one"},
        {"type": "bullet", "text": "Bullet two"},
        {"type": "bullet", "text": "Bullet three"},
    ]


def test_summarizer_handles_non_bullet_output(sample_article):
    def fake_runner(prompt: str, cfg: SummarizerConfig) -> str:
        return "Bullet one. Bullet two. Bullet three."

    result = summarize_article(sample_article, runner=fake_runner)
    texts = [block["text"] for block in result["summary"]]
    assert texts == ["Bullet one.", "Bullet two.", "Bullet three."]


def test_summarizer_raises_on_failure(sample_article):
    def failing_runner(prompt: str, cfg: SummarizerConfig) -> str:
        raise RuntimeError("boom")

    with pytest.raises(SummarizerError):
        summarize_article(sample_article, runner=failing_runner)
