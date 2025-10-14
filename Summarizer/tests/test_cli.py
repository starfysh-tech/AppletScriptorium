from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from Summarizer import cli


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
