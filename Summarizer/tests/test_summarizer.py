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


# --- LM Studio model resolution (loaded model wins, glm preferred) ---

def _patch_lmstudio_inventory(monkeypatch, loaded, downloaded, preferred=("zai-org/glm-4.6v-flash",), pin=None):
    from Summarizer import summarizer as S
    monkeypatch.setattr(S, "_get_active_llms", lambda base_url: list(loaded))
    monkeypatch.setattr(S, "_get_loaded_models", lambda base_url: list(downloaded))
    monkeypatch.setattr(S, "LMSTUDIO_PREFERRED_MODELS", list(preferred))
    monkeypatch.setattr(S, "LMSTUDIO_MODEL", pin)


def test_resolve_explicit_override_wins(monkeypatch):
    from Summarizer.summarizer import resolve_lmstudio_model
    _patch_lmstudio_inventory(monkeypatch, loaded=["zai-org/glm-4.6v-flash"], downloaded=[])
    assert resolve_lmstudio_model("http://x", "qwen/qwen3.5-9b") == "qwen/qwen3.5-9b"


def test_resolve_prefers_glm_when_loaded_alongside_others(monkeypatch):
    from Summarizer.summarizer import resolve_lmstudio_model
    _patch_lmstudio_inventory(monkeypatch, loaded=["kurtis", "zai-org/glm-4.6v-flash"], downloaded=[])
    assert resolve_lmstudio_model("http://x") == "zai-org/glm-4.6v-flash"


def test_resolve_uses_whatever_is_loaded(monkeypatch):
    from Summarizer.summarizer import resolve_lmstudio_model
    _patch_lmstudio_inventory(monkeypatch, loaded=["mistral-7b"], downloaded=["mistral-7b", "zai-org/glm-4.6v-flash"])
    assert resolve_lmstudio_model("http://x") == "mistral-7b"


def test_resolve_falls_back_to_downloaded_preferred_then_pin(monkeypatch):
    from Summarizer.summarizer import resolve_lmstudio_model, SummarizerError
    _patch_lmstudio_inventory(monkeypatch, loaded=[], downloaded=["zai-org/glm-4.6v-flash"])
    assert resolve_lmstudio_model("http://x") == "zai-org/glm-4.6v-flash"
    _patch_lmstudio_inventory(monkeypatch, loaded=[], downloaded=["other"], pin="pinned-model")
    assert resolve_lmstudio_model("http://x") == "pinned-model"
    _patch_lmstudio_inventory(monkeypatch, loaded=[], downloaded=["other"])
    with pytest.raises(SummarizerError):
        resolve_lmstudio_model("http://x")


def test_ensure_loaded_loads_downloaded_but_inactive_model(monkeypatch):
    from Summarizer import summarizer as S
    calls = []
    active = {"now": []}
    monkeypatch.setattr(S, "_get_active_llms", lambda base_url: list(active["now"]))
    monkeypatch.setattr(S, "_get_loaded_models", lambda base_url: ["qwen/qwen3.5-9b"])
    import time
    monkeypatch.setattr(time, "sleep", lambda s: None)  # the loader sleeps 2s after lms load

    def fake_run(cmd, **kw):
        calls.append(cmd)
        active["now"] = ["qwen/qwen3.5-9b"]  # load takes effect
        class R: returncode = 0; stdout = ""; stderr = ""
        return R()
    monkeypatch.setattr(S.subprocess, "run", fake_run)

    ok, msg = S._ensure_correct_model_loaded("http://x", "qwen/qwen3.5-9b")
    assert ok and "Loaded" in msg
    assert calls and "load" in calls[0] and "qwen/qwen3.5-9b" in calls[0]

    # Already active: no lms call
    calls.clear()
    ok, msg = S._ensure_correct_model_loaded("http://x", "qwen/qwen3.5-9b")
    assert ok and not calls

    # Not even downloaded: fail without calling lms
    ok, msg = S._ensure_correct_model_loaded("http://x", "nope")
    assert not ok and not calls


def test_fit_max_tokens_refuses_when_prompt_fills_context(monkeypatch):
    from Summarizer import summarizer as S
    monkeypatch.setattr(S, "_lmstudio_context_length", lambda base_url, model: 1000)
    prompt = "word " * 100
    fitted = S._fit_max_tokens("http://x", "m", prompt, 16384)
    # Behavioural properties, not the formula: the request is shrunk below what
    # was asked, still leaves a usable completion, and fits the window with
    # the prompt (LM Studio's own accounting on a real request was ~700
    # prompt tokens for 2.5k chars, well under this estimate).
    assert 256 <= fitted < 16384
    assert S._estimate_tokens(prompt) + fitted <= 1000
    # Unknown context: the request is passed through untouched
    monkeypatch.setattr(S, "_lmstudio_context_length", lambda base_url, model: None)
    assert S._fit_max_tokens("http://x", "m", prompt, 16384) == 16384
    # Prompt that fills the window: refuse rather than send a doomed request
    monkeypatch.setattr(S, "_lmstudio_context_length", lambda base_url, model: 1000)
    with pytest.raises(S.SummarizerError):
        S._fit_max_tokens("http://x", "m", "word " * 600, 16384)


def test_estimate_tokens_counts_non_ascii_per_char():
    from Summarizer.summarizer import _estimate_tokens, _truncate_to_tokens
    assert _estimate_tokens("abcdef") == 2
    assert _estimate_tokens("日本語のテキスト") == 8
    assert _estimate_tokens(_truncate_to_tokens("日本語" * 100, 50)) <= 50
