from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from Summarizer import cli
from Summarizer.article_fetcher import FetchConfig, FetchError
from Summarizer.summarizer import SummarizerConfig


@pytest.fixture
def sample_summary() -> dict:
    return {
        "title": "Sample Title",
        "url": "https://example.com/article",
        "publisher": "Example News",
        "snippet": "Short blurb",
        "summary": [
            {"type": "bullet", "text": "bullet one"},
            {"type": "bullet", "text": "bullet two"},
            {"type": "bullet", "text": "bullet three"},
        ],
        "model": "test-model",
    }


def test_cli_run_pipeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_summary: dict):
    def fake_capture(path: Path, subject_filter=None) -> None:
        path.write_text("dummy", encoding="utf-8")

    def fake_load_links(path: Path):
        return [{"title": "Sample Title", "url": "https://example.com/article", "publisher": "Example News", "snippet": "Short blurb"}]

    def fake_process(links, output_dir, fetch_cfg, sum_cfg, max_articles=None):
        (output_dir / "articles").mkdir(exist_ok=True)
        return [sample_summary], [
            {"url": "https://blocked.example", "reason": "HTTP 403"}
        ]

    sent = {}

    def fake_send(output_dir, recipients, sender):
        sent["output_dir"] = output_dir
        sent["recipients"] = recipients
        sent["sender"] = sender

    monkeypatch.setattr(cli, "capture_alert", fake_capture)
    monkeypatch.setattr(cli, "load_links", fake_load_links)
    monkeypatch.setattr(cli, "process_articles", fake_process)
    monkeypatch.setattr(cli, "send_digest_email", fake_send)

    args = argparse.Namespace(
        command="run",
        output_dir=str(tmp_path),
        model="test-model",
        max_articles=None,
        subject_filter=None,
        email_digest=["ops@example.com"],
        email_sender="alerts@example.com",
    )

    cli.run_pipeline(args)

    assert (tmp_path / "alert.tsv").exists()
    assert (tmp_path / "digest.html").exists()
    assert (tmp_path / "digest.txt").exists()
    assert (tmp_path / "summaries.json").exists()

    digest_txt = (tmp_path / "digest.txt").read_text(encoding="utf-8")
    assert "Missing articles" in digest_txt
    assert "- https://blocked.example — HTTP 403" in digest_txt

    log_text = (tmp_path / "workflow.log").read_text(encoding="utf-8")
    assert "https://blocked.example" in log_text
    assert sent["recipients"] == ["ops@example.com"]
    assert sent["sender"] == "alerts@example.com"


def test_cli_run_pipeline_env_recipients(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_summary: dict):
    def fake_capture(path: Path, subject_filter=None) -> None:
        path.write_text("dummy", encoding="utf-8")

    def fake_load_links(path: Path):
        return [{"title": "Sample Title", "url": "https://example.com/article", "publisher": "Example News", "snippet": "Short blurb"}]

    def fake_process(links, output_dir, fetch_cfg, sum_cfg, max_articles=None):
        (output_dir / "articles").mkdir(exist_ok=True)
        return [sample_summary], []

    sent = {}

    def fake_send(output_dir, recipients, sender):
        sent["recipients"] = recipients
        sent["sender"] = sender

    monkeypatch.setattr(cli, "capture_alert", fake_capture)
    monkeypatch.setattr(cli, "load_links", fake_load_links)
    monkeypatch.setattr(cli, "process_articles", fake_process)
    monkeypatch.setattr(cli, "send_digest_email", fake_send)
    monkeypatch.setenv("ALERT_DIGEST_EMAIL", "one@example.com, two@example.com")

    args = argparse.Namespace(
        command="run",
        output_dir=str(tmp_path),
        model="test-model",
        max_articles=None,
        subject_filter=None,
        email_digest=None,
        email_sender=None,
    )

    cli.run_pipeline(args)

    assert sorted(sent["recipients"]) == ["one@example.com", "two@example.com"]
    assert sent["sender"] is None


def test_process_articles_and_render_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    links = [
        {
            "title": "Alpha Study Highlights Remote Monitoring",
            "url": "https://example.org/alpha",
            "publisher": "Clinical Daily",
            "snippet": "Remote tools double survey completion in oncology clinics.",
        },
        {
            "title": "Beta Report on PRO Barriers",
            "url": "https://example.org/beta",
            "publisher": "",
            "snippet": "",
        },
    ]

    article_html = {
        "https://example.org/alpha": "<html><body><article><p>Alpha remote monitoring results.</p></article></body></html>",
        "https://example.org/beta": "<html><body><article><p>Beta report details barriers to scaling.</p></article></body></html>",
    }

    def fake_fetch(url: str, cfg: FetchConfig):
        assert isinstance(cfg, FetchConfig)
        return article_html[url]

    def fake_summarize(article_payload: dict, config: SummarizerConfig):
        assert article_payload["content"]
        return {
            "title": article_payload["title"],
            "url": article_payload["url"],
            "publisher": article_payload.get("publisher", ""),
            "snippet": article_payload.get("snippet", ""),
            "summary": [
                {"type": "bullet", "text": "**KEY FINDING**: " + article_payload["title"]},
                {"type": "bullet", "text": "**TACTICAL WIN [SHIP NOW]**: Launch remote coaching workflow."},
                {"type": "bullet", "text": "**MARKET SIGNAL [🟡 NOTABLE]**: Payers are rewarding PRO programs."},
                {"type": "bullet", "text": "**CONCERN**: Teams must budget for support training."},
            ],
            "model": config.model,
        }

    monkeypatch.setattr(cli, "fetch_article", fake_fetch)
    monkeypatch.setattr(cli, "summarize_article", fake_summarize)

    output_dir = tmp_path
    summaries, failures = cli.process_articles(links, output_dir, FetchConfig(), SummarizerConfig())

    assert failures == []
    assert {summary["url"] for summary in summaries} == {
        "https://example.org/alpha",
        "https://example.org/beta",
    }

    articles_dir = output_dir / "articles"
    assert articles_dir.exists()
    html_files = sorted(p.name for p in articles_dir.glob("*.html"))
    assert html_files == [
        "01-alpha-study-highlights-remote-monitoring.html",
        "02-beta-report-on-pro-barriers.html",
    ]

    cli.render_outputs(summaries, failures, output_dir)

    digest_html = (output_dir / "digest.html").read_text(encoding="utf-8")
    assert "Alpha Study Highlights Remote Monitoring" in digest_html
    assert "Beta Report on PRO Barriers" in digest_html

    digest_txt = (output_dir / "digest.txt").read_text(encoding="utf-8")
    assert "Google Alert Intelligence" in digest_txt

    summaries_payload = json.loads((output_dir / "summaries.json").read_text(encoding="utf-8"))
    assert sorted(entry["url"] for entry in summaries_payload) == sorted([
        "https://example.org/alpha",
        "https://example.org/beta",
    ])


def test_process_articles_records_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    links = [
        {
            "title": "Challenging Article",
            "url": "https://example.org/challenge",
        }
    ]

    def failing_fetch(url: str, cfg: FetchConfig):
        raise FetchError(url, "HTTP 403")

    monkeypatch.setattr(cli, "fetch_article", failing_fetch)

    summaries, failures = cli.process_articles(links, tmp_path, FetchConfig(), SummarizerConfig())

    assert summaries == []
    assert failures == [{"url": "https://example.org/challenge", "reason": "HTTP 403"}]

    cli.render_outputs(summaries, failures, tmp_path)
    digest_text = (tmp_path / "digest.txt").read_text(encoding="utf-8")
    assert "Missing articles" in digest_text
    assert "https://example.org/challenge" in digest_text


def test_send_digest_email_creates_eml(tmp_path: Path):
    (tmp_path / "digest.html").write_text("<html><body><p>Digest body</p></body></html>", encoding="utf-8")

    cli.send_digest_email(tmp_path, ["ops@example.com", "pm@example.com"], sender=None)

    eml_path = tmp_path / "digest.eml"
    assert eml_path.exists()

    from email.header import decode_header
    from email.parser import Parser

    message = Parser().parsestr(eml_path.read_text(encoding="utf-8"))
    assert message["To"] == "ops@example.com"
    assert message["From"] == "ops@example.com"
    decoded_subject = "".join(
        fragment.decode(charset or "utf-8") if isinstance(fragment, bytes) else fragment
        for fragment, charset in decode_header(message["Subject"])
    )
    assert decoded_subject.startswith("Google Alert Intelligence")
    payload = message.get_payload()
    if isinstance(payload, list):
        payload = payload[0].get_payload()
    assert "Digest body" in payload


def test_send_digest_email_requires_recipient(tmp_path: Path):
    (tmp_path / "digest.html").write_text("<html></html>", encoding="utf-8")

    with pytest.raises(ValueError):
        cli.send_digest_email(tmp_path, [], sender=None)
