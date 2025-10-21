from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import List

import pytest

from Summarizer import cli
from Summarizer.article_fetcher import FetchConfig, FetchError, FetchOutcome
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

    def fake_load_links(path: Path) -> List[dict]:
        return [{
            "title": "Sample Title",
            "url": "https://example.com/article",
            "publisher": "Example News",
            "snippet": "Short blurb",
        }]

    def fake_process(links, output_dir, fetch_cfg, sum_cfg, max_articles=None):
        (output_dir / "articles").mkdir(exist_ok=True)
        return [sample_summary], [
            {"url": "https://blocked.example", "reason": "HTTP 403"}
        ]

    sent = {}

    def fake_send(output_dir, recipients, sender, topic=None):
        sent["output_dir"] = output_dir
        sent["recipients"] = recipients
        sent["sender"] = sender
        sent["topic"] = topic

    monkeypatch.setattr(cli, "capture_alert", fake_capture)
    monkeypatch.setattr(cli, "load_links", fake_load_links)
    monkeypatch.setattr(cli, "process_articles", fake_process)
    monkeypatch.setattr(cli, "send_digest_email", fake_send)
    monkeypatch.delenv("ALERT_DIGEST_EMAIL", raising=False)

    args = argparse.Namespace(
        command="run",
        output_dir=str(tmp_path),
        model="test-model",
        max_articles=None,
        subject_filter=None,
        email_digest=["ops@example.com"],
        email_sender="alerts@example.com",
        smtp_send=False,
        topic=None,
    )

    cli.run_pipeline(args)

    assert (tmp_path / "alert.tsv").exists()
    assert (tmp_path / "digest.html").exists()
    assert (tmp_path / "digest.txt").exists()
    assert (tmp_path / "summaries.json").exists()

    digest_txt = (tmp_path / "digest.txt").read_text(encoding="utf-8")
    assert "Missing articles" in digest_txt
    assert "https://blocked.example" in digest_txt

    log_text = (tmp_path / "workflow.log").read_text(encoding="utf-8")
    assert "https://blocked.example" in log_text
    assert sent["recipients"] == ["ops@example.com"]
    assert sent["sender"] == "alerts@example.com"


def test_cli_run_pipeline_env_recipients(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_summary: dict):
    def fake_capture(path: Path, subject_filter=None) -> None:
        path.write_text("dummy", encoding="utf-8")

    def fake_load_links(path: Path) -> List[dict]:
        return [{
            "title": "Sample Title",
            "url": "https://example.com/article",
            "publisher": "Example News",
            "snippet": "Short blurb",
        }]

    def fake_process(links, output_dir, fetch_cfg, sum_cfg, max_articles=None):
        (output_dir / "articles").mkdir(exist_ok=True)
        return [sample_summary], []

    sent = {}

    def fake_send(output_dir, recipients, sender, topic=None):
        sent["recipients"] = recipients
        sent["sender"] = sender
        sent["topic"] = topic

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
        smtp_send=False,
        topic=None,
    )

    cli.run_pipeline(args)

    assert sorted(sent["recipients"]) == ["one@example.com", "two@example.com"]
    assert sent["sender"] is None


def test_process_articles_html_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
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
        "https://example.org/alpha": "<html><body><article><p>Alpha remote monitoring results show significant improvements in patient engagement across diverse clinical settings. The study tracked over 500 participants across multiple clinical sites over a twelve-month period. Remote tools were found to double survey completion rates in oncology clinics, with particular success in capturing patient-reported outcomes during treatment cycles. Researchers noted that digital platforms enabled real-time data collection and analysis, leading to more responsive care adjustments and improved clinical decision-making. The findings suggest that technology-enabled monitoring can bridge gaps in traditional care delivery models and improve overall treatment outcomes for cancer patients undergoing active therapy regimens. Patient satisfaction scores increased by an average of 25 percent when remote monitoring was integrated into standard care protocols. Healthcare providers reported that the additional data helped identify complications earlier and reduced emergency room visits by nearly 30 percent among enrolled participants.</p></article></body></html>",
        "https://example.org/beta": "<html><body><article><p>Beta report details barriers to scaling patient-reported outcome programs across healthcare systems in both urban and rural settings. Key challenges identified include technical infrastructure limitations, staff training requirements, and integration with existing electronic health record systems that vary significantly across institutions. The report emphasizes that successful implementation requires strong organizational commitment and dedicated resources for ongoing maintenance and support throughout the deployment lifecycle. Healthcare administrators must balance the proven benefits of PRO collection against the operational costs and workflow disruptions during rollout phases that can span multiple years. Several case studies demonstrate that phased deployment strategies yield better adoption rates compared to system-wide launches, particularly when implementation teams prioritize user feedback and iterative improvements based on real-world experience. Organizations that invested in comprehensive training programs and provided ongoing technical support saw significantly higher clinician engagement and patient participation rates over time.</p></article></body></html>",
    }

    last_url = {"value": None}

    def fake_fetch(url: str, cfg: FetchConfig):
        last_url["value"] = url
        return article_html[url]

    def fake_outcome():
        url = last_url["value"]
        assert url is not None
        return FetchOutcome(
            content=article_html[url],
            strategy="httpx",
            format="html",
            duration=0.1,
        )

    def fake_summarize(article_payload: dict, config: SummarizerConfig):
        assert article_payload["content"]
        return {
            "title": article_payload["title"],
            "url": article_payload["url"],
            "publisher": article_payload.get("publisher", ""),
            "snippet": article_payload.get("snippet", ""),
            "summary": [{"type": "bullet", "text": "Test"}],
            "model": config.model,
        }

    monkeypatch.setattr(cli, "fetch_article", fake_fetch)
    monkeypatch.setattr(cli, "get_last_fetch_outcome", fake_outcome)
    monkeypatch.setattr(cli, "summarize_article", fake_summarize)

    summaries, failures = cli.process_articles(links, tmp_path, FetchConfig(), SummarizerConfig())

    assert failures == []
    assert len(summaries) == 2

    articles_dir = tmp_path / "articles"
    html_files = sorted(p.name for p in articles_dir.glob("*.html"))
    assert html_files == [
        "01-alpha-study-highlights-remote-monitoring.html",
        "02-beta-report-on-pro-barriers.html",
    ]

    fallback_files = list(articles_dir.glob("*.fallback.md"))
    assert fallback_files == []

    content_files = sorted(p.name for p in articles_dir.glob("*.content.md"))
    assert len(content_files) == 2


def test_process_articles_markdown_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
    links = [{"title": "Blocked Article", "url": "https://blocked.example"}]

    markdown_body = """# Blocked Article

This is fallback content retrieved using the url-to-md CLI tool for sites that block direct HTTP access. The article discusses various aspects of patient care and clinical outcomes measurement in modern healthcare settings. Remote monitoring technologies have revolutionized how clinicians track patient progress between office visits. Digital health platforms enable real-time data collection and analysis, providing insights that were previously unavailable. Healthcare systems are increasingly adopting these tools to improve care quality and patient satisfaction. Implementation challenges include technical integration, staff training, and ensuring patient engagement with new technologies. Successful programs typically feature strong leadership support, adequate resources, and iterative refinement based on user feedback."""

    def fake_fetch(url: str, cfg: FetchConfig):
        return markdown_body

    def fake_outcome():
        return FetchOutcome(
            content=markdown_body,
            strategy="url-to-md",
            format="markdown",
            duration=5.0,
            removed_sections=["More MTN"],
        )

    def fake_summarize(article_payload: dict, config: SummarizerConfig):
        return {
            "title": article_payload["title"],
            "url": article_payload["url"],
            "summary": [{"type": "bullet", "text": "Test"}],
            "model": config.model,
        }

    monkeypatch.setattr(cli, "fetch_article", fake_fetch)
    monkeypatch.setattr(cli, "get_last_fetch_outcome", fake_outcome)
    monkeypatch.setattr(cli, "summarize_article", fake_summarize)

    with caplog.at_level(logging.INFO):
        summaries, failures = cli.process_articles(links, tmp_path, FetchConfig(), SummarizerConfig())

    assert failures == []
    assert len(summaries) == 1

    articles_dir = tmp_path / "articles"
    assert not any(articles_dir.glob("*.html"))

    fallback_file = articles_dir / "01-blocked-article.fallback.md"
    assert fallback_file.exists()
    assert fallback_file.read_text(encoding="utf-8") == markdown_body

    content_file = articles_dir / "01-blocked-article.content.md"
    assert content_file.exists()
    assert content_file.read_text(encoding="utf-8") == markdown_body

    joined_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "strategy=url-to-md" in joined_logs
    assert "format=markdown" in joined_logs


def test_process_articles_records_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    links = [{"title": "Challenging Article", "url": "https://example.org/challenge"}]

    def failing_fetch(url: str, cfg: FetchConfig):
        raise FetchError(url, "HTTP 403")

    monkeypatch.setattr(cli, "fetch_article", failing_fetch)
    monkeypatch.setattr(cli, "get_last_fetch_outcome", lambda: None)

    summaries, failures = cli.process_articles(links, tmp_path, FetchConfig(), SummarizerConfig())

    assert summaries == []
    assert failures == [{"url": "https://example.org/challenge", "reason": "HTTP 403"}]


def test_workflow_log_includes_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
    links = [{"title": "Alpha", "url": "https://example.org/a"}]
    html_body = "<html><body><p>Alpha</p></body></html>"

    def fake_fetch(url: str, cfg: FetchConfig):
        return html_body

    def fake_outcome():
        return FetchOutcome(
            content=html_body,
            strategy="httpx",
            format="html",
            duration=0.1,
        )

    def fake_summarize(article_payload: dict, config: SummarizerConfig):
        return {
            "title": article_payload["title"],
            "url": article_payload["url"],
            "summary": [{"type": "bullet", "text": "Test"}],
            "model": config.model,
        }

    monkeypatch.setattr(cli, "fetch_article", fake_fetch)
    monkeypatch.setattr(cli, "get_last_fetch_outcome", fake_outcome)
    monkeypatch.setattr(cli, "summarize_article", fake_summarize)

    with caplog.at_level(logging.INFO):
        cli.process_articles(links, tmp_path, FetchConfig(), SummarizerConfig())

    joined_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "strategy=httpx" in joined_logs
    assert "Fetch summary: httpx=1" in joined_logs
