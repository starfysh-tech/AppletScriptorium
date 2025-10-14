# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AppletScriptorium is a macOS automation framework that uses AppleScript, shell scripts, and Python to build agents that automate local workflows. The first agent, **Summarizer**, monitors Mail.app for Google Alerts on any topic you choose, extracts article links, fetches pages, summarizes them with a local LLM (Ollama), and generates intelligent email digests. Mail rule conditions handle all topic filtering—the code is generic and processes whatever alert triggers it.

## Architecture

### Pipeline Flow
1. **Alert Capture** — Mail rule saves triggering message (automated) OR `fetch-alert-source.applescript` captures inbox message with optional subject filter (manual CLI)
2. **Link Extraction** (`link_extractor.py`) — Parses email HTML, extracts article URLs with metadata
3. **Article Fetching** (`article_fetcher.py` + `crawlee_fetcher.py`) — HTTP fetcher with Playwright fallback for Cloudflare-protected sites; parallel processing (max 5 workers)
4. **Content Cleaning** (`content_cleaner.py`) — Converts HTML to readable Markdown using readability-lxml
5. **Summarization** (`summarizer.py`) — Calls local Ollama (granite4:tiny-h model) for structured 4-bullet summaries
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
- `Summarizer/crawlee_fetcher.py` — Playwright fallback (subprocess isolation)
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
python3 -m pip list | grep -E "beautifulsoup4|httpx|readability|crawlee"
```

## Key Technical Details

### Mail Rule Automation
- Event-driven: processes alerts immediately when they arrive (any Google Alert topic)
- Mail rule conditions filter by From/Subject (e.g., `From: googlealerts-noreply@google.com`, `Subject: Google Alert -`)
- AppleScript (`process-alert.scpt`) saves triggering message, runs Python pipeline, creates and sends HTML digest email
- Code is topic-agnostic—Mail rule conditions do ALL filtering
- See `Summarizer/MAIL_RULE_SETUP.md` for configuration details

### Article Fetching Strategy
- Primary: httpx with user-agent headers
- Fallback: Crawlee + Playwright for Cloudflare-protected domains (extended wait times: 13-18s for JS/challenges)
- Parallel processing: ThreadPoolExecutor with max 5 workers (~70% faster than sequential)
- In-memory caching for the life of the process
- Custom headers via `ALERT_HTTP_HEADERS_JSON` env var: `'{"example.com": {"Cookie": "session=abc"}}'`

### Summarization
- Requires local Ollama installation with `granite4:tiny-h` model pulled
- Model can be overridden via `--model` CLI flag or `ALERT_MODEL` env var
- Returns structured 4-bullet format: KEY FINDING, TACTICAL WIN [tag], MARKET SIGNAL [tag], CONCERN
- Digest includes executive summary and cross-article insights
- Works with any Google Alert topic—summaries adapt to content

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
- **Crawlee subprocess**: `crawlee_fetcher.py` spawns subprocess to avoid event loop conflicts
- **Fixture regeneration**: Run `refresh-fixtures.py` after modifying parsers, diff before committing
- **PYTHONPATH**: Only set in shell wrappers for inline scripts; NOT needed for `-m` invocation
- **System permissions**: Different modes require different permissions:
  - **Mail rule automation**: Accessibility (System Settings → Privacy & Security → Accessibility → enable Mail.app)
  - **Manual CLI usage**: Automation (System Settings → Privacy & Security → Automation → enable Terminal → Mail)
  - **Both modes**: Need both permissions

## Documentation Location Guide

- **Setup/Installation**: See `SETUP.md`
- **Usage/CLI examples**: See `README.md`
- **Mail rule configuration**: See `Summarizer/MAIL_RULE_SETUP.md`
- **Architecture/PRD**: See `Summarizer/PRO Alert Summarizer PRD.md`
- **This file**: Claude Code behavior guidance only
