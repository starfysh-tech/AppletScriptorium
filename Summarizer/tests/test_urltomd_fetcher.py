from __future__ import annotations

import os
import subprocess

import pytest

from Summarizer.urltomd_fetcher import UrlToMdConfig, UrlToMdError, fetch_with_urltomd


def fake_popen(monkeypatch: pytest.MonkeyPatch, *, returncode=0, stdout="", stderr="", communicate_error=None, popen_error=None):
    captured = {}

    class FakePopen:
        pid = 999999

        def __init__(self, args, **kwargs):
            if popen_error:
                raise popen_error
            captured["args"] = args
            self.returncode = returncode

        def communicate(self, timeout=None):
            if communicate_error:
                raise communicate_error
            return stdout, stderr

        def wait(self, timeout=None):
            return self.returncode

        def kill(self):
            pass

    monkeypatch.setattr(subprocess, "Popen", FakePopen)
    # The timeout path signals the process group; keep it off real processes
    monkeypatch.setattr(os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(os, "killpg", lambda pgid, sig: None)
    return captured


def test_urltomd_builds_command(monkeypatch: pytest.MonkeyPatch):
    captured = fake_popen(monkeypatch, stdout="# Title\n\nBody")

    fetch_with_urltomd("https://example.com", UrlToMdConfig(timeout=5))

    args = captured["args"]
    assert args[0] == "url-to-md"
    assert "https://example.com" in args
    assert "--include-tags" in args
    assert "p" in args
    assert "--remove-tags" in args
    assert "nav" in args


def test_urltomd_timeout(monkeypatch: pytest.MonkeyPatch):
    fake_popen(monkeypatch, communicate_error=subprocess.TimeoutExpired("url-to-md", timeout=5))

    with pytest.raises(UrlToMdError) as exc:
        fetch_with_urltomd("https://slow.example", UrlToMdConfig(timeout=5))

    assert "timeout" in str(exc.value).lower()


def test_urltomd_missing_binary(monkeypatch: pytest.MonkeyPatch):
    fake_popen(monkeypatch, popen_error=FileNotFoundError("url-to-md"))

    with pytest.raises(UrlToMdError) as exc:
        fetch_with_urltomd("https://example.com", UrlToMdConfig())

    assert "not found" in str(exc.value).lower()


def test_urltomd_nonzero_exit(monkeypatch: pytest.MonkeyPatch):
    fake_popen(monkeypatch, returncode=1, stderr="Blocked")

    with pytest.raises(UrlToMdError) as exc:
        fetch_with_urltomd("https://blocked.example", UrlToMdConfig())

    assert "Blocked" in str(exc.value)


def test_urltomd_returns_markdown(monkeypatch: pytest.MonkeyPatch):
    fake_popen(monkeypatch, stdout="# Success\n\nMarkdown")

    result = fetch_with_urltomd("https://example.com", UrlToMdConfig())
    assert result == "# Success\n\nMarkdown"
