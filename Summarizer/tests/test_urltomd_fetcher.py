from __future__ import annotations

import subprocess

import pytest

from Summarizer.urltomd_fetcher import UrlToMdConfig, UrlToMdError, fetch_with_urltomd


def test_urltomd_builds_command(monkeypatch: pytest.MonkeyPatch):
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args

        class FakeResult:
            returncode = 0
            stdout = "# Title\n\nBody"
            stderr = ""

        return FakeResult()

    monkeypatch.setattr(subprocess, "run", fake_run)

    fetch_with_urltomd("https://example.com", UrlToMdConfig(timeout=5))

    args = captured["args"]
    assert args[0] == "url-to-md"
    assert "https://example.com" in args
    assert "--include-tags" in args
    assert "p" in args
    assert "--remove-tags" in args
    assert "nav" in args


def test_urltomd_timeout(monkeypatch: pytest.MonkeyPatch):
    def fake_run(args, **kwargs):
        raise subprocess.TimeoutExpired(args, timeout=5)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(UrlToMdError) as exc:
        fetch_with_urltomd("https://slow.example", UrlToMdConfig(timeout=5))

    assert "timeout" in str(exc.value).lower()


def test_urltomd_missing_binary(monkeypatch: pytest.MonkeyPatch):
    def fake_run(args, **kwargs):
        raise FileNotFoundError("url-to-md")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(UrlToMdError) as exc:
        fetch_with_urltomd("https://example.com", UrlToMdConfig())

    assert "not found" in str(exc.value).lower()


def test_urltomd_nonzero_exit(monkeypatch: pytest.MonkeyPatch):
    def fake_run(args, **kwargs):
        class FakeResult:
            returncode = 1
            stdout = ""
            stderr = "Blocked"

        return FakeResult()

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(UrlToMdError) as exc:
        fetch_with_urltomd("https://blocked.example", UrlToMdConfig())

    assert "Blocked" in str(exc.value)


def test_urltomd_returns_markdown(monkeypatch: pytest.MonkeyPatch):
    def fake_run(args, **kwargs):
        class FakeResult:
            returncode = 0
            stdout = "# Success\n\nMarkdown"
            stderr = ""

        return FakeResult()

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = fetch_with_urltomd("https://example.com", UrlToMdConfig())
    assert result == "# Success\n\nMarkdown"
