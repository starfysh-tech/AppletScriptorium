from __future__ import annotations

import httpx
import pytest

from Summarizer.article_fetcher import FetchConfig, FetchError, clear_cache, fetch_article


@pytest.fixture(autouse=True)
def reset_cache():
    clear_cache()
    yield
    clear_cache()


def test_fetch_caches_network_response(monkeypatch: pytest.MonkeyPatch):
    calls = {"count": 0}

    def fake_get(url: str, timeout: float, follow_redirects: bool, headers):
        calls["count"] += 1

        class FakeResponse:
            status_code = 200
            text = "<html>ok</html>"

            def raise_for_status(self):
                return None

        return FakeResponse()

    monkeypatch.setattr(httpx, "get", fake_get)

    cfg = FetchConfig()
    first = fetch_article("https://cache.example", cfg)
    second = fetch_article("https://cache.example", cfg)
    assert first == second == "<html>ok</html>"
    assert calls["count"] == 1


def test_fetch_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch):
    request = httpx.Request("GET", "https://retry.example")
    attempts = {"count": 0}

    def fake_get(url: str, timeout: float, follow_redirects: bool, headers):
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

    def fake_get(url: str, timeout: float, follow_redirects: bool, headers):
        raise httpx.RequestError("fail", request=request)

    monkeypatch.setattr(httpx, "get", fake_get)

    with pytest.raises(FetchError) as exc:
        fetch_article("https://fail.example", FetchConfig(max_retries=1))

    assert "exhausted retries" in str(exc.value)


def test_fetch_logs_status(monkeypatch: pytest.MonkeyPatch):
    class FakeResponse:
        status_code = 403
        text = "Forbidden"

        def raise_for_status(self):
            raise httpx.HTTPStatusError("status", request=httpx.Request("GET", "https://blocked"), response=self)

    def fake_get(url: str, timeout: float, follow_redirects: bool, headers):
        return FakeResponse()

    monkeypatch.setattr(httpx, "get", fake_get)

    with pytest.raises(FetchError) as exc:
        fetch_article("https://blocked", FetchConfig(max_retries=0))

    assert "HTTP 403" in str(exc.value)


def test_fetch_includes_env_headers(monkeypatch: pytest.MonkeyPatch):
    def fake_get(url: str, timeout: float, follow_redirects: bool, headers):
        assert headers.get("Cookie") == "session=abc"

        class FakeResponse:
            status_code = 200
            text = "<html>ok</html>"

            def raise_for_status(self):
                return None

        return FakeResponse()

    monkeypatch.setenv("ALERT_HTTP_HEADERS_JSON", '{"example.com": {"Cookie": "session=abc"}}')
    monkeypatch.setattr(httpx, "get", fake_get)

    fetch_article("https://example.com/path", FetchConfig(allow_cache=False))


def test_fetch_crawlee_fallback(monkeypatch: pytest.MonkeyPatch):
    url = "https://dailynews.ascopubs.org/foo"

    request = httpx.Request("GET", url)
    response = httpx.Response(403, request=request, text="challenge")

    def fake_get(url: str, timeout: float, follow_redirects: bool, headers):
        raise httpx.HTTPStatusError("blocked", request=request, response=response)

    monkeypatch.setattr(httpx, "get", fake_get)

    called = {}

    def fake_crawlee(target_url: str, config):
        called["url"] = target_url
        called["timeout"] = config.timeout
        return "<html>rendered</html>"

    # Inject fake Crawlee helper and domain mapping (to be provided by implementation)
    monkeypatch.setattr("Summarizer.article_fetcher.fetch_with_crawlee_sync", fake_crawlee, raising=False)
    monkeypatch.setattr("Summarizer.article_fetcher._CRAWLEE_DOMAINS", {"dailynews.ascopubs.org"}, raising=False)

    content = fetch_article(url, FetchConfig(allow_cache=False, max_retries=0))
    assert content == "<html>rendered</html>"
    assert called["url"] == url
    assert called["timeout"] >= 60.0


def test_fetch_headless_failure_raises(monkeypatch: pytest.MonkeyPatch):
    url = "https://dailynews.ascopubs.org/foo"

    request = httpx.Request("GET", url)
    response = httpx.Response(403, request=request, text="challenge")

    def fake_get(url: str, timeout: float, follow_redirects: bool, headers):
        raise httpx.HTTPStatusError("blocked", request=request, response=response)

    monkeypatch.setattr(httpx, "get", fake_get)

    from Summarizer.crawlee_fetcher import CrawleeFetchError

    def fake_crawlee(target_url: str, config):
        raise CrawleeFetchError("crawlee unavailable")

    monkeypatch.setattr("Summarizer.article_fetcher.fetch_with_crawlee_sync", fake_crawlee, raising=False)
    monkeypatch.setattr("Summarizer.article_fetcher._CRAWLEE_DOMAINS", {"dailynews.ascopubs.org"}, raising=False)

    with pytest.raises(FetchError) as exc:
        fetch_article(url, FetchConfig(allow_cache=False, max_retries=0))

    assert "crawlee unavailable" in str(exc.value)
