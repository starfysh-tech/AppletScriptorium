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
    assert "Google Alert Intelligence" in html_output
    assert "ASCO Daily News" in html_output
    # Single article: no executive summary section (3 article bullets only)
    assert html_output.count("<li>bullet") == 3
    # Header shows article count
    assert "1 article from 1 source" in html_output


def test_render_digest_text():
    text_output = render_digest_text([SAMPLE_SUMMARY])
    lines = text_output.splitlines()
    assert lines[0].startswith("Google Alert Intelligence —")
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


def test_insights_request_free_text_not_summary_schema(monkeypatch):
    from Summarizer import summarizer
    from Summarizer.digest_renderer import generate_cross_article_insights

    calls = {}

    def fake_run(prompt, cfg, **kwargs):
        calls.update(kwargs)
        return "- Theme one\n- Theme two"

    monkeypatch.setattr(summarizer, "_run_with_lmstudio", fake_run)
    articles = [
        {**SAMPLE_SUMMARY, "url": f"https://site{i}.example/a", "title": f"Article {i}"}
        for i in range(3)
    ]

    assert generate_cross_article_insights(articles) == ["Theme one", "Theme two"]
    assert calls == {"response_format": None}


def test_lmstudio_omits_response_format_when_none(monkeypatch):
    from Summarizer import summarizer

    sent = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "- insight"}}]}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def post(self, url, json):
            sent.update(json)
            return FakeResponse()

    monkeypatch.setattr(summarizer, "LMSTUDIO_BASE_URL", "http://lmstudio.test")
    monkeypatch.setattr(summarizer, "resolve_lmstudio_model", lambda base, model: "m")
    monkeypatch.setattr(summarizer, "ensure_correct_model_loaded", lambda base, model: (True, "ok"))
    monkeypatch.setattr(summarizer, "_fit_max_tokens", lambda base, model, prompt, requested: requested)
    monkeypatch.setattr(summarizer.httpx, "Client", FakeClient)

    cfg = summarizer.SummarizerConfig(model=None, temperature=0.3, max_tokens=64)
    assert summarizer._run_with_lmstudio("p", cfg, response_format=None) == "- insight"
    assert "response_format" not in sent
    summarizer._run_with_lmstudio("p", cfg, response_format=summarizer.SUMMARY_JSON_SCHEMA)
    assert sent["response_format"] == summarizer.SUMMARY_JSON_SCHEMA


def test_topic_is_escaped_in_html():
    html_output = render_digest_html([SAMPLE_SUMMARY], topic="<script>x</script>")
    assert "<script>x</script>" not in html_output
    assert "&lt;script&gt;" in html_output


def test_bold_label_keeps_other_markup_escaped():
    article = {**SAMPLE_SUMMARY, "summary": [{"type": "bullet", "text": "**KEY FINDING**: uses <b>raw</b> tags"}]}
    html_output = render_digest_html([article])
    assert "<b>KEY FINDING:</b>" in html_output
    assert "&lt;b&gt;raw&lt;/b&gt;" in html_output
