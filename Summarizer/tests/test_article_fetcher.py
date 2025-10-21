from __future__ import annotations

import httpx
import pytest

from Summarizer.article_fetcher import (
    FetchConfig,
    FetchError,
    clear_cache,
    fetch_article,
    get_last_fetch_outcome,
)


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
            headers = {'content-type': 'text/html'}

            def raise_for_status(self):
                return None

        return FakeResponse()

    monkeypatch.setattr(httpx, "get", fake_get)

    cfg = FetchConfig()
    first = fetch_article("https://cache.example", cfg)
    outcome_first = get_last_fetch_outcome()
    second = fetch_article("https://cache.example", cfg)
    outcome_second = get_last_fetch_outcome()

    assert first == second == "<html>ok</html>"
    assert calls["count"] == 1
    assert outcome_first is not None and outcome_first.strategy == "httpx"
    assert outcome_second is not None and outcome_second.strategy == "httpx-cache"


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
            headers = {'content-type': 'text/html'}

            def raise_for_status(self):
                return None

        return FakeResponse()

    monkeypatch.setattr(httpx, "get", fake_get)

    content = fetch_article("https://retry.example", FetchConfig(max_retries=5))
    outcome = get_last_fetch_outcome()

    assert content == "<html>recovered</html>"
    assert attempts["count"] == 3
    assert outcome is not None and outcome.strategy == "httpx"


def test_fetch_raises_after_exhausting_retries(monkeypatch: pytest.MonkeyPatch):
    request = httpx.Request("GET", "https://fail.example")

    def fake_get(url: str, timeout: float, follow_redirects: bool, headers):
        raise httpx.RequestError("fail", request=request)

    monkeypatch.setattr(httpx, "get", fake_get)

    with pytest.raises(FetchError) as exc:
        fetch_article("https://fail.example", FetchConfig(max_retries=1))

    assert "exhausted retries" in str(exc.value)


def test_fetch_includes_env_headers(monkeypatch: pytest.MonkeyPatch):
    def fake_get(url: str, timeout: float, follow_redirects: bool, headers):
        assert headers.get("Cookie") == "session=abc"

        class FakeResponse:
            status_code = 200
            text = "<html>ok</html>"
            headers = {'content-type': 'text/html'}

            def raise_for_status(self):
                return None

        return FakeResponse()

    monkeypatch.setenv("ALERT_HTTP_HEADERS_JSON", '{"example.com": {"Cookie": "session=abc"}}')
    monkeypatch.setattr(httpx, "get", fake_get)

    fetch_article("https://example.com/path", FetchConfig(allow_cache=False))


def test_markdown_fallback_returns_markdown(monkeypatch: pytest.MonkeyPatch):
    url = "https://blocked.example"
    request = httpx.Request("GET", url)
    response = httpx.Response(403, request=request, text="Forbidden")

    def fake_get(url: str, timeout: float, follow_redirects: bool, headers):
        raise httpx.HTTPStatusError("blocked", request=request, response=response)

    def fake_urltomd(target_url: str, config):
        return "# Article\n\nMarkdown content"

    def fake_cleanup(md: str):
        return md, []

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr("Summarizer.article_fetcher.fetch_with_urltomd", fake_urltomd)
    monkeypatch.setattr("Summarizer.article_fetcher.clean_markdown_content", fake_cleanup)

    content = fetch_article(url, FetchConfig(allow_cache=False, max_retries=0))
    outcome = get_last_fetch_outcome()

    assert content.startswith("# Article")
    assert outcome is not None
    assert outcome.format == "markdown"
    assert outcome.strategy == "url-to-md"


def test_markdown_fallback_uses_cache(monkeypatch: pytest.MonkeyPatch):
    url = "https://blocked.example"
    request = httpx.Request("GET", url)
    response = httpx.Response(403, request=request, text="Forbidden")
    call_count = {"urltomd": 0}

    def fake_get(url: str, timeout: float, follow_redirects: bool, headers):
        raise httpx.HTTPStatusError("blocked", request=request, response=response)

    def fake_urltomd(target_url: str, config):
        call_count["urltomd"] += 1
        return "# Cached\n\nContent"

    def fake_cleanup(md: str):
        return md, []

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr("Summarizer.article_fetcher.fetch_with_urltomd", fake_urltomd)
    monkeypatch.setattr("Summarizer.article_fetcher.clean_markdown_content", fake_cleanup)

    fetch_article(url, FetchConfig(max_retries=0))
    outcome_first = get_last_fetch_outcome()
    fetch_article(url, FetchConfig(max_retries=0))
    outcome_second = get_last_fetch_outcome()

    assert call_count["urltomd"] == 1
    assert outcome_first is not None and outcome_first.strategy == "url-to-md"
    assert outcome_second is not None and outcome_second.strategy == "url-to-md-cache"


def test_jina_fallback_invoked(monkeypatch: pytest.MonkeyPatch):
    url = "https://blocked.example"
    request = httpx.Request("GET", url)
    response = httpx.Response(503, request=request, text="Retry later")

    def fake_get(url: str, timeout: float, follow_redirects: bool, headers):
        raise httpx.HTTPStatusError("blocked", request=request, response=response)

    def fake_urltomd(target_url: str, config):
        from Summarizer.urltomd_fetcher import UrlToMdError

        raise UrlToMdError(target_url, "blocked")

    def fake_jina(target_url: str, config):
        return "# Jina Result\n\nContent"

    def fake_cleanup(md: str):
        return md, ["More MTN"]

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr("Summarizer.article_fetcher.fetch_with_urltomd", fake_urltomd)
    monkeypatch.setattr("Summarizer.article_fetcher.fetch_with_jina", fake_jina)
    monkeypatch.setattr("Summarizer.article_fetcher.clean_markdown_content", fake_cleanup)

    content = fetch_article(url, FetchConfig(max_retries=0))
    outcome = get_last_fetch_outcome()

    assert content.startswith("# Jina Result")
    assert outcome is not None
    assert outcome.strategy == "jina"
    assert outcome.removed_sections == ["More MTN"]


def test_fallback_chain_errors(monkeypatch: pytest.MonkeyPatch):
    url = "https://blocked.example"
    request = httpx.Request("GET", url)
    response = httpx.Response(403, request=request, text="Forbidden")

    def fake_get(url: str, timeout: float, follow_redirects: bool, headers):
        raise httpx.HTTPStatusError("blocked", request=request, response=response)

    def fake_urltomd(target_url: str, config):
        from Summarizer.urltomd_fetcher import UrlToMdError

        raise UrlToMdError(target_url, "blocked")

    def fake_jina(target_url: str, config):
        from Summarizer.jina_fetcher import JinaFetchError

        raise JinaFetchError(target_url, "down")

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr("Summarizer.article_fetcher.fetch_with_urltomd", fake_urltomd)
    monkeypatch.setattr("Summarizer.article_fetcher.fetch_with_jina", fake_jina)

    with pytest.raises(FetchError) as exc:
        fetch_article(url, FetchConfig(max_retries=0, allow_cache=False))

    assert "fallback failed" in str(exc.value)
