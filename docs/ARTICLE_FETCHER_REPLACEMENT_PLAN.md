# Article Fetcher Replacement - Technical Implementation Plan

## Executive Summary

- **Goal**: Drop the Crawlee/Playwright fallback and still defeat Cloudflare/PerimeterX so Summarizer keeps producing clean Markdown for the LLM.
- **Status**: httpx straight fetch works (`runs/alert-20251015-103635/workflow.log#L1`), but naive Markdown fallbacks smear the nav/ads the HTML cleaner normally strips (`ghana.md#L1`).
- **Recommendation**: Keep the HTML contract for happy-path fetches. When we must fall back, pull Markdown through `url-to-md`/Jina with aggressive tag filters, scrub it with a lightweight cleanup helper, cache it separately, and deliver the cleaned Markdown straight to the summarizer while skipping readability. No tuple refactor required.

## Current Pipeline & Observed Outputs

- `Summarizer/article_fetcher.py` returns HTML today; `_process_single_article()` saves `<slug>.html`, then `content_cleaner.extract_content()` converts HTML → Markdown via readability + BeautifulSoup + markdownify.
- Sample run `runs/alert-20251015-103635` proves this path is clean: compare the raw HTML (`articles/01-mtn-...crowns-.html#L1`) with the generated Markdown (`articles/01-mtn-...crowns-.content.md#L1`).
- Raw `url-to-md` output (`ghana.md#L1`) is full of “Contact us” links and ad slots—structure the HTML cleaner depended on is already gone. With targeted CLI flags (`--include-tags p h2 h3 h4 img --remove-tags nav header footer aside script --clean-content`) we can get much closer (`ghana-include-p2.md#L1`), but “More MTN Ghana News” still lingers.

## Proposed Implementation

### 1. URL-to-MD wrapper (new module)

- Create `Summarizer/urltomd_fetcher.py` with a thin subprocess wrapper around `url-to-md`.
- Default command: `url-to-md <url> --include-tags p h2 h3 h4 img --remove-tags nav header footer aside script --clean-content`.
- Handle missing binary, timeouts, and blocked pages with friendly errors (`UrlToMdError`).

### 2. Jina fallback (existing research)

- Keep the lightweight HTTP client (no browser). Expect Markdown output with a metadata header.
- Expose `fetch_with_jina(url, JinaConfig)` raising `JinaFetchError` on failure (existing pseudocode already solid; reuse).

### 3. Markdown cleanup (new)

- New file `Summarizer/markdown_cleanup.py` with `clean_markdown_content(markdown: str) -> tuple[str, list[str]]` (cleaned Markdown + removed section headers).
- Start with regex stop-patterns for common boilerplate (BusinessGhana contact blocks, `## More ...` headings); make it easy to extend through configuration/tests.
- Normalization rules should trim whitespace, collapse duplicate blank lines, and leave the writing unchanged so the summarizer receives what the fallback tool produced minus navigation clutter. No Markdown→HTML conversion occurs in this module.

### 4. Refresh `article_fetcher`

- Keep signature: `fetch_article(...) -> str` so existing callers/tests keep compiling.
- Drop Crawlee imports, `_should_use_crawlee()`, `_requires_headed_mode()`, `CRAWLEE_*` constants.
- Add imports for the new helpers plus `URLTOMD_TIMEOUT` / `JINA_TIMEOUT` in `config.py`, `perf_counter` from `time`, `dataclass`, `Literal`, `field`, and `threading.local`.
- Introduce a thread-local telemetry channel and dual caches:
  ```python
  @dataclass(slots=True)
  class FetchOutcome:
      content: str
      strategy: Literal["httpx", "url-to-md", "jina", "url-to-md-cache"]
      format: Literal["html", "markdown"]
      duration: float
      removed_sections: list[str] = field(default_factory=list)

  _FETCH_CONTEXT = threading.local()
  _CACHE_HTML: dict[str, str] = {}
  _CACHE_MARKDOWN: dict[str, str] = {}

  def get_last_fetch_outcome() -> FetchOutcome | None:
      return getattr(_FETCH_CONTEXT, "outcome", None)
  ```
- Logging: every attempt emits `[fetch][strategy=<...>] url (duration=...s)`.
- In the retry loop:
  1. Try httpx as today (reuse `_CACHE_HTML` when `allow_cache=True`). Store `FetchOutcome(..., format="html")` once successful.
  2. On 403/429/503 (or after exhausting retries), call `_fetch_markdown_fallback(url, allow_cache)`:
     ```python
     def _fetch_markdown_fallback(url: str, allow_cache: bool) -> FetchOutcome:
         if allow_cache and url in _CACHE_MARKDOWN:
             cleaned = _CACHE_MARKDOWN[url]
             return FetchOutcome(
                 content=cleaned,
                 strategy="url-to-md-cache",
                 format="markdown",
                 duration=0.0,
             )

         start = perf_counter()
         try:
             markdown = fetch_with_urltomd(url, UrlToMdConfig(timeout=URLTOMD_TIMEOUT))
             strategy = "url-to-md"
         except UrlToMdError:
             markdown = fetch_with_jina(url, JinaConfig(timeout=JINA_TIMEOUT))
             strategy = "jina"
         cleaned, removed = clean_markdown_content(markdown)
         elapsed = perf_counter() - start
         if allow_cache:
             _CACHE_MARKDOWN[url] = cleaned
         return FetchOutcome(
             content=cleaned,
             strategy=strategy,
             format="markdown",
             duration=elapsed,
             removed_sections=removed,
         )
     ```
  3. For fallback outcomes, store the `FetchOutcome` in thread-local metadata and return `outcome.content` (Markdown).
- `clear_cache()` should wipe both dictionaries; add `clear_markdown_cache()` helper for targeted resets (useful in tests).
- Provide `get_last_fetch_outcome()` for CLI/tests to read telemetry immediately after calling `fetch_article()` on the same thread.
### 5. CLI adjustments

- `_process_single_article()` now branches on the fetch format exposed by `FetchOutcome`:
  ```python
  content = fetch_article(url, fetch_cfg)
  outcome = get_last_fetch_outcome()
  if outcome is None:
      raise RuntimeError("fetch metadata missing")

  html_path = articles_dir / f"{slug}.html"
  fallback_md_path = articles_dir / f"{slug}.fallback.md"
  content_path = articles_dir / f"{slug}.content.md"

  if outcome.format == "html":
      html_path.write_text(content, encoding="utf-8")
      cleaned_md = extract_content(content)
  else:
      fallback_md_path.write_text(content, encoding="utf-8")
      html_path.unlink(missing_ok=True)  # only keep HTML artifact for true HTML sources
      cleaned_md = content

  content_path.write_text(cleaned_md, encoding="utf-8")
  ```
- Only materialize `<slug>.html` when the source really was HTML. Markdown fallbacks produce `<slug>.fallback.md` (cleaned Markdown) and skip readability entirely, while `<slug>.content.md` remains the canonical summarizer input for both paths.
- Log `[fetch][strategy=<...>][format=<...>][duration=...s] url` immediately after each fetch (include `removed=<len(outcome.removed_sections)>`). Accumulate a `Counter` and emit a summary (`"Fetch summary: httpx=5, url-to-md=2, jina=0"`) at the end of the run.
- Ensure the summarizer always receives Markdown: HTML path continues flowing through `extract_content()`, Markdown path uses the cleaned Markdown directly. Optionally run a `validate_markdown_content()` helper to warn when fallback markdown looks suspiciously empty/short.
### 6. Configuration cleanup

- Remove Crawlee constants from `Summarizer/config.py`.
- Introduce:
  ```python
  URLTOMD_TIMEOUT = 10.0
  JINA_TIMEOUT = 30.0
  ```
- Update comments to document the new chain (`httpx → url-to-md → Jina`).

### 7. Dependency hygiene

- Delete `Summarizer/crawlee_fetcher.py`, related scripts, and references.
- Remove `crawlee`, `browserforge`, and Playwright dependencies from requirements.
- Ensure `url-to-md` is documented as a system dependency (see README/setup script).

## Validation Plan

1. **Unit tests**
   - `test_urltomd_fetcher.py`: command composition, timeout handling, missing binary.
   - `test_markdown_cleanup.py`: fixtures covering `ghana.md` → expect nav headers stripped, removed section list populated, and validation helper warnings when content is suspicious.
   - `test_article_fetcher.py`:
     - httpx success path unchanged (cache hit assertions intact).
     - Markdown fallback path returns Markdown (assert outcome.format == "markdown") and `get_last_fetch_outcome()` reports the chosen strategy plus removed sections.
     - Confirm fallback caching works: first call populates `_CACHE_MARKDOWN`, second call with `allow_cache=True` hits the cache and reports `strategy="url-to-md-cache"`.

2. **CLI tests**
   - Patch `fetch_article` to use the new thread-local outcome helper (e.g., set `_FETCH_CONTEXT.outcome` inside the fake) to simulate url-to-md fallback.
   - Assert `_process_single_article()` writes `<slug>.fallback.md` and that the workflow log includes per-article `[fetch][strategy=url-to-md]` plus the final `"Fetch summary: ..."` line.

3. **Manual check**
   - `python3 -m Summarizer.cli run --output-dir runs/fallback --max-articles 1` on a blocked domain.
   - Compare raw url-to-md output with `articles/<slug>.fallback.md` (cleaned Markdown) and the resulting `articles/<slug>.content.md` to confirm nav removal (e.g., no “Contact us” or “More MTN Ghana”).
   - Verify digest quality hasn’t regressed.
   - Inspect `workflow.log` for per-article `[fetch][strategy=...]` entries and the final summary line.

4. **Regression**
   - Run existing pytest suite to confirm nothing else broke.

## Open Questions / Follow-ups

- Should we persist the intermediate Markdown for auditing, or rely on logs + HTML artifacts?
- Need to monitor new nav patterns and extend `_STOP_PATTERNS` over time.
- If url-to-md remains slow on some domains, consider caching its CLI binary path or exploring `curl_cffi` as a pure-Python fallback later.
