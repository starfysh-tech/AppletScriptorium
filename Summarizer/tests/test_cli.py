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
    def fake_capture(path: Path) -> None:
        path.write_text("dummy", encoding="utf-8")

    def fake_load_links(path: Path):
        return [{"title": "Sample Title", "url": "https://example.com/article", "publisher": "Example News", "snippet": "Short blurb"}]

    def fake_process(links, output_dir, fetch_cfg, sum_cfg, max_articles=None):
        (output_dir / "articles").mkdir(exist_ok=True)
        return [sample_summary]

    monkeypatch.setattr(cli, "capture_alert", fake_capture)
    monkeypatch.setattr(cli, "load_links", fake_load_links)
    monkeypatch.setattr(cli, "process_articles", fake_process)

    args = argparse.Namespace(
        command="run",
        output_dir=str(tmp_path),
        stub_manifest=None,
        model="test-model",
        max_articles=None,
    )

    cli.run_pipeline(args)

    assert (tmp_path / "alert.tsv").exists()
    assert (tmp_path / "digest.html").exists()
    assert (tmp_path / "digest.txt").exists()
    assert (tmp_path / "summaries.json").exists()
