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
        return """- **KEY FINDING**: Bullet one
- **TACTICAL WIN [Production]**: Bullet two
- **MARKET SIGNAL [Adoption]**: Bullet three
- **CONCERN**: Bullet four"""

    result = summarize_article(sample_article, config=SummarizerConfig(model="qwen3:latest"), runner=fake_runner)
    assert len(result["summary"]) == 4
    assert result["summary"][0]["text"] == "**KEY FINDING**: Bullet one"
    assert result["summary"][1]["text"] == "**TACTICAL WIN [Production]**: Bullet two"
    assert result["summary"][2]["text"] == "**MARKET SIGNAL [Adoption]**: Bullet three"
    assert result["summary"][3]["text"] == "**CONCERN**: Bullet four"


def test_summarizer_handles_non_bullet_output(sample_article):
    def fake_runner(prompt: str, cfg: SummarizerConfig) -> str:
        return "**KEY FINDING**: One. **TACTICAL WIN [tag]**: Two. **MARKET SIGNAL [tag]**: Three. **CONCERN**: Four."

    result = summarize_article(sample_article, runner=fake_runner)
    texts = [block["text"] for block in result["summary"]]
    assert len(texts) == 4
    assert "**KEY FINDING**" in texts[0]
    assert "**TACTICAL WIN" in texts[1]
    assert "**MARKET SIGNAL" in texts[2]
    assert "**CONCERN**" in texts[3]


def test_summarizer_raises_on_failure(sample_article):
    def failing_runner(prompt: str, cfg: SummarizerConfig) -> str:
        raise RuntimeError("boom")

    with pytest.raises(SummarizerError):
        summarize_article(sample_article, runner=failing_runner)
