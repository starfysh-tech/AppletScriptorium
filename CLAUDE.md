# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AppletScriptorium is a macOS automation framework that uses AppleScript, shell scripts, and Python to build agents that automate local workflows. The first agent, **Summarizer**, monitors Mail.app for Google Alerts on any topic you choose, extracts article links, fetches pages, summarizes them with a local LLM (Ollama), and generates intelligent email digests. Mail rule conditions handle all topic filtering—the code is generic and processes whatever alert triggers it.

## Architecture

### Pipeline Flow
1. **Alert Capture** — Mail rule saves triggering message (automated) OR `fetch-alert-source.applescript` captures inbox message with optional subject filter (manual CLI)
2. **Link Extraction** (`link_extractor.py`) — Parses email HTML, extracts article URLs with metadata
3. **Article Fetching** (`article_fetcher.py` + `urltomd_fetcher.py`) — HTTP fetcher with Markdown fallbacks (url-to-md / Jina) for protection bypass; parallel processing (max 5 workers)
4. **Content Cleaning** (`content_cleaner.py`) — Converts HTML to readable Markdown using readability-lxml
5. **Summarization** (`summarizer.py`) — Calls local Ollama for structured 4-bullet summaries
6. **Digest Rendering** (`digest_renderer.py`) — Generates HTML and plaintext email digests with executive summary and cross-article insights
7. **CLI Orchestration** (`cli.py`) — Ties all steps together with logging, error handling, and parallel execution

### Module Organization
- Each agent lives in its own top-level directory (currently `Summarizer/`)
- Fixtures live in `Summarizer/Samples/` and anchor regression tests
- Future shared utilities will move to `shared/` when multiple agents need them

## Core Files Reference

### Entry Points
- `Summarizer/cli.py` — Main orchestrator, invoke with `python3 -m Summarizer.cli run`
- `Summarizer/fetch-alert-source.applescript` — Captures inbox messages (manual CLI)
- `Summarizer/templates/process-alert.scpt` — Mail rule automation script

### Pipeline Modules
- `Summarizer/link_extractor.py` — `extract_links(eml_path)` → list of article dicts
- `Summarizer/article_fetcher.py` — `fetch_article(url)` → HTML string, `clear_cache()` for tests
- `Summarizer/urltomd_fetcher.py` — url-to-md CLI wrapper for Markdown fallbacks
- `Summarizer/jina_fetcher.py` — Jina Reader API wrapper as final fallback
- `Summarizer/markdown_cleanup.py` — Clean/validate Markdown from fallbacks
- `Summarizer/content_cleaner.py` — `extract_content(html)` → Markdown text
- `Summarizer/summarizer.py` — `summarize_article(article_dict)` → structured summary
- `Summarizer/digest_renderer.py` — `render_digest_html(summaries)`, `render_digest_text(summaries)`

### Test Fixtures
- `Summarizer/Samples/google-alert-sample-2025-10-06.eml` — Raw email source
- `Summarizer/Samples/google-alert-sample-2025-10-06-links.tsv` — Expected link extraction
- `Summarizer/tests/` — Pytest suite using fixture-based validation

### Configuration
- `Summarizer/config.py` — Central configuration (model, timeouts, domain lists, parallelism, HTTP headers)

## Development Patterns

### Python Execution
- **Always** use module invocation: `python3 -m Summarizer.cli` (NOT `python3 Summarizer/cli.py`)
- Reason: Relative imports (`from .article_fetcher import ...`) require package mode
- System Python with `--user` flag for dependencies (venv not compatible with Mail rule automation)

### Testing Approach
- Fixture-based: Committed samples in `Summarizer/Samples/` anchor regression tests
- Run tests: `python3 -m pytest Summarizer/tests`
- Refresh fixtures: `Summarizer/refresh-fixtures.py`
- Mock external calls: `article_fetcher` has in-memory cache, call `clear_cache()` between tests

### Parallel Processing
- Uses `ThreadPoolExecutor` with max 5 workers for article fetch/summarize
- Pattern: `concurrent.futures.as_completed()` for progress tracking
- See `cli.py` lines 150-180 for reference implementation

### AppleScript Constraints
- **Cannot activate venv** — Mail.app scripts run in restricted sandbox, must use system Python
- **Tab indentation** — AppleScript uses tabs, not spaces
- **Validation** — Run `osascript -s` to check syntax before committing
- **Python path** — Now uses `which python3` for Intel/Apple Silicon portability (process-alert.scpt:29)

### Common Bash Commands
```bash
# Run all tests
python3 -m pytest Summarizer/tests

# Test specific module
python3 -m pytest Summarizer/tests/test_link_extractor.py -v

# Refresh fixtures after parser changes
Summarizer/refresh-fixtures.py

# Parse alert and view links
python3 Summarizer/clean-alert.py Summarizer/Samples/google-alert-sample-2025-10-06.eml | head

# Check AppleScript syntax
osascript -s Summarizer/templates/process-alert.scpt

# Validate system Python packages
python3 -m pip list | grep -E "beautifulsoup4|httpx|readability"

# Run sequential workflow (alternative to CLI)
./run_workflow.sh
```

## Key Technical Details

### Mail Rule Automation
- Event-driven: processes alerts immediately when they arrive (any Google Alert topic)
- Mail rule conditions filter by From/Subject (e.g., `From: googlealerts-noreply@google.com`, `Subject: Google Alert -`)
- AppleScript (`process-alert.scpt`) saves triggering message, runs Python pipeline, creates and sends HTML digest email
- Code is topic-agnostic—Mail rule conditions do ALL filtering
- See `docs/SETUP.md` (Mail Rule Automation section) for configuration details

### Article Fetching Strategy
- Primary: httpx with user-agent headers
- Fallback chain for bot-protected sites (403/429/503 errors):
  1. `url-to-md` CLI (Markdown output with Cloudflare bypass)
  2. Jina Reader API (final fallback, requires `JINA_API_KEY` env var)
- Dual caching: HTML cache for httpx, Markdown cache for fallbacks
- Parallel processing: ThreadPoolExecutor with max 5 workers (~70% faster than sequential)
- Custom headers via `ALERT_HTTP_HEADERS_JSON` env var: `'{"example.com": {"Cookie": "session=abc"}}'`

### Summarization
- Requires local Ollama installation with `qwen3:latest` model pulled
- Model can be overridden via `--model` CLI flag or `ALERT_MODEL` env var
- Returns structured 4-bullet format: KEY FINDING, TACTICAL WIN [tag], MARKET SIGNAL [tag], CONCERN
- Digest includes executive summary and cross-article insights
- Works with any Google Alert topic—summaries adapt to content

**Ollama Health Detection & Auto-Recovery** (`Summarizer/summarizer.py:_run_with_ollama`):
- **Timeout**: `OLLAMA_TIMEOUT = 120.0` (seconds) — detects unresponsive daemon
- **Detection**: Logs `"Ollama unresponsive (timeout after 120s); attempting restart"`
- **Auto-restart**: Kills stuck process via `pkill -f "ollama serve"`; launchd auto-relaunches
- **Fallback**: If pkill fails, attempts `brew services restart ollama`
- **Retry**: Retries summarization once after restart attempt
- **Failure**: If still unresponsive, raises `SummarizerError` with clear diagnostic message
- **Tuning**: Adjust `OLLAMA_TIMEOUT` in `config.py` if needed (e.g., slow hardware)

## Coding Conventions

- **Python**: PEP 8, 4-space indents, snake_case for functions/variables
- **Scripts**: kebab-case filenames (e.g., `fetch-alert-source.applescript`)
- **AppleScript**: Include header comments describing trigger conditions and dependencies
- **Commits**: Imperative subjects <60 chars (e.g., `summarizer: add link parser`)
- Prefer pure functions and dependency injection for testability
- Keep fixtures sanitized; never commit production emails or secrets

## Working Agreement

- Ship the simplest solution that works on local macOS
- Avoid premature abstractions until multiple agents need them
- Add logging, error handling, idempotency, and locking when relevant
- Document configuration requirements (env vars, subjects) in README and PRD
- Provide script usage examples or tests with each change
- Document simplifying assumptions inline or in PRD
- **Breaking changes policy**: No backward compatibility maintained—breaking changes documented in release notes only

## Common Gotchas

- **AppleScript Mail rules**: Cannot use venv, must use system Python with `--user` packages
- **Python imports**: Must use `-m Summarizer.cli` for relative imports to work
- **Markdown fallback cache**: `article_fetcher._CACHE_MARKDOWN` stores cleaned Markdown per URL
- **Fixture regeneration**: Run `refresh-fixtures.py` after modifying parsers, diff before committing
- **PYTHONPATH**: Only set in shell wrappers for inline scripts; NOT needed for `-m` invocation
- **System permissions**: Different modes require different permissions:
  - **Mail rule automation**: Accessibility (System Settings → Privacy & Security → Accessibility → enable Mail.app)
  - **Manual CLI usage**: Automation (System Settings → Privacy & Security → Automation → enable Terminal → Mail)
  - **Both modes**: Need both permissions
- **Ollama unresponsiveness**: After extended uptime, Ollama may become stuck. Pipeline auto-detects (120s timeout) and kills/restarts it. If this fails, manually run `pkill -f "ollama serve"` (launchd will auto-restart)

## Module Integration Examples

### Article Fetching

Use `Summarizer/article_fetcher.py` in scripts or REPL sessions:

```python
from Summarizer.article_fetcher import fetch_article, FetchConfig

# Basic fetch
html = fetch_article("https://example.com/article", FetchConfig())

# With custom headers for authenticated sites
import json
import os
os.environ['ALERT_HTTP_HEADERS_JSON'] = json.dumps({
    "example.com": {"Cookie": "session=abc"}
})
html = fetch_article("https://example.com/article", FetchConfig())
```

**Key points:**
- Dual caching: `_CACHE_HTML` for httpx, `_CACHE_MARKDOWN` for fallbacks
- Call `article_fetcher.clear_cache()` in tests to reset both caches
- Automatic Markdown fallback (url-to-md → Jina) on 403/429/503 errors
- `get_last_fetch_outcome()` returns `FetchOutcome` with strategy/format/duration metadata
- Custom headers via `ALERT_HTTP_HEADERS_JSON` environment variable

### Content Extraction

Convert HTML to clean Markdown:

```python
from pathlib import Path
from Summarizer.content_cleaner import extract_content

html = Path('Summarizer/Samples/articles/pro-diction-models.html').read_text(encoding='utf-8')
markdown = extract_content(html)
print(markdown.splitlines()[0])  # First line
```

### Summary Generation

Call local Ollama for structured summaries:

```python
from Summarizer.summarizer import summarize_article, SummarizerConfig
from Summarizer.content_cleaner import extract_content

article = {
    "title": "Article Title",
    "url": "https://example.com/article",
    "content": extract_content(html),
}
summary = summarize_article(article, SummarizerConfig())
```

Requires Ollama running (`brew services start ollama`) with model pulled (`ollama pull qwen3:latest`).

### Digest Assembly

Generate HTML and plaintext digests:

```python
from Summarizer.digest_renderer import render_digest_html, render_digest_text

summaries = [
    {
        "title": "Article Title",
        "url": "https://example.com",
        "summary": [
            {"type": "bullet", "text": "**KEY FINDING**: Main insight"},
        ],
        "model": "qwen3:latest",
    }
]

html = render_digest_html(summaries)
text = render_digest_text(summaries)
```

## Fixture Management

### Refreshing Test Fixtures

When parser logic changes:

```bash
# Rebuild from committed .eml file
Summarizer/refresh-fixtures.py

# Or generate to temp files for diffing
Summarizer/refresh-fixtures.py \
  --links /tmp/alert-links.tsv \
  --links-json /tmp/alert-links.json \
  --html /tmp/alert.html

# Diff against committed fixtures
diff -u Summarizer/Samples/google-alert-sample-2025-10-06-links.tsv /tmp/alert-links.tsv
```

### Capturing New Fixtures

Capture fresh alert email from Mail.app inbox:

```bash
# With subject filter
osascript Summarizer/fetch-alert-source.applescript \
  Summarizer/Samples/google-alert-sample-2025-10-06.eml \
  "Medication reminder"

# Without filter (most recent inbox message)
osascript Summarizer/fetch-alert-source.applescript \
  Summarizer/Samples/google-alert-sample-2025-10-06.eml
```

**Important**: Sanitize emails before committing (remove personal info, sensitive URLs).

## Documentation Location Guide

- **Setup/Installation**: See `docs/SETUP.md`
- **Usage/CLI examples**: See `README.md`
- **Troubleshooting**: See `docs/TROUBLESHOOTING.md`
- **Mail rule configuration**: See `docs/SETUP.md` (Mail Rule Automation section)
- **This file**: Claude Code behavior guidance only
