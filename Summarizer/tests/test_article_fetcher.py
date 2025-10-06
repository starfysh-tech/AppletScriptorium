from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from article_fetcher import FetchConfig, FetchError, clear_cache, fetch_article


@pytest.fixture(autouse=True)
def reset_cache():
    clear_cache()
    yield
    clear_cache()


def test_fetch_uses_stub_manifest(tmp_path: Path):
    stub_html = tmp_path / "example.html"
    stub_html.write_text("<html>stub-content</html>", encoding="utf-8")

    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"https://example.com": "example.html"}), encoding="utf-8")

    content = fetch_article("https://example.com", FetchConfig(stub_manifest=manifest))
    assert "stub-content" in content


def test_fetch_caches_network_response(monkeypatch: pytest.MonkeyPatch):
    calls = {"count": 0}

    def fake_get(url: str, timeout: float, follow_redirects: bool):
        calls["count"] += 1

        class FakeResponse:
            status_code = 200
            text = "<html>ok</html>"

            def raise_for_status(self):
                return None

        return FakeResponse()

    monkeypatch.setattr(httpx, "get", fake_get)

    cfg = FetchConfig(stub_manifest=None)
    first = fetch_article("https://cache.example", cfg)
    second = fetch_article("https://cache.example", cfg)
    assert first == second == "<html>ok</html>"
    assert calls["count"] == 1


def test_fetch_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch):
    request = httpx.Request("GET", "https://retry.example")
    attempts = {"count": 0}

    def fake_get(url: str, timeout: float, follow_redirects: bool):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise httpx.RequestError("boom", request=request)

        class FakeResponse:
            status_code = 200
            text = "<html>recovered</html>"

            def raise_for_status(self):
                return None

        return FakeResponse()

    monkeypatch.setattr(httpx, "get", fake_get)

    content = fetch_article("https://retry.example", FetchConfig(max_retries=5))
    assert content == "<html>recovered</html>"
    assert attempts["count"] == 3


def test_fetch_raises_after_exhausting_retries(monkeypatch: pytest.MonkeyPatch):
    request = httpx.Request("GET", "https://fail.example")

    def fake_get(url: str, timeout: float, follow_redirects: bool):
        raise httpx.RequestError("fail", request=request)

    monkeypatch.setattr(httpx, "get", fake_get)

    with pytest.raises(FetchError) as exc:
        fetch_article("https://fail.example", FetchConfig(max_retries=1))

    assert "exhausted retries" in str(exc.value)
