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

## Development Commands

### Environment Setup
```bash
# Create virtual environment
python3 -m venv .venv && source .venv/bin/activate

# Install Python dependencies
python3 -m pip install -r Summarizer/requirements.txt

# Install Playwright for Cloudflare-protected sites (one-time)
python3 -m playwright install
```

### Testing
```bash
# Run all tests
python3 -m pytest Summarizer/tests

# Run specific test file
python3 -m pytest Summarizer/tests/test_link_extractor.py

# Run with verbose output
python3 -m pytest -v
```

### Fixture Management
```bash
# Refresh raw alert fixture (captures most recent message matching subject)
# Works with any Google Alert topic
osascript Summarizer/fetch-alert-source.applescript \
  Summarizer/Samples/google-alert-sample-2025-10-06.eml \
  "Medication reminder"

# Rebuild decoded HTML and expected link list
Summarizer/refresh-fixtures.py

# Validate changes against committed fixtures
Summarizer/refresh-fixtures.py --links /tmp/alert-links.tsv --links-json /tmp/alert-links.json --html /tmp/alert.html
diff -u Summarizer/Samples/google-alert-sample-2025-10-06-links.tsv /tmp/alert-links.tsv
```

### Running the Pipeline

#### CLI (preferred)
```bash
# Full pipeline with subject filter (captures most recent matching inbox message)
# Works with any Google Alert topic
python3 -m Summarizer.cli run \
  --output-dir runs/$(date +%Y%m%d-%H%M%S) \
  --subject-filter "Medication reminder"

# Without filter (captures most recent inbox message)
python3 -m Summarizer.cli run --output-dir runs/$(date +%Y%m%d-%H%M%S)

# With article limit and custom model (AI research example)
python3 -m Summarizer.cli run \
  --output-dir runs/test \
  --max-articles 5 \
  --model granite4:tiny-h \
  --subject-filter "Artificial intelligence"

# Email digest to recipients (matches all Google Alert topics with broad pattern)
python3 -m Summarizer.cli run \
  --output-dir runs/latest \
  --email-digest user@example.com \
  --email-sender user@example.com \
  --subject-filter "Google Alert -"
```

#### Shell Wrapper (alternative)
```bash
# Run via bash script (creates timestamped directory in runs/)
./run_workflow.sh
```

### Quick Validation
```bash
# Parse alert and view links (TSV format)
python3 Summarizer/clean-alert.py Summarizer/Samples/google-alert-sample-2025-10-06.eml | head

# Parse alert and view links (JSON format)
python3 Summarizer/clean-alert.py --format json Summarizer/Samples/google-alert-sample-2025-10-06.eml | jq '.' | head
```

## Key Technical Details

### AppleScript Integration
- **Manual CLI:** `fetch-alert-source.applescript` accepts optional subject filter as second argument; captures most recent matching inbox message
- **Mail rule automation:** `process-pro-alert.scpt` runs when Mail rule triggers; saves the triggering message directly (bypasses fetch-alert-source.applescript)
- Mail rule conditions (From/Subject) do all filtering; no hardcoded subject patterns in scripts
- AppleScript files must be executable or run via `osascript`

### Article Fetching Strategy
- Primary: httpx with user-agent headers
- Fallback: Crawlee + Playwright for Cloudflare-protected domains (extended wait times: 13-18s for JS/challenges)
- Parallel processing: ThreadPoolExecutor with max 5 workers (~70% faster than sequential)
- In-memory caching for the life of the process
- Custom headers via `PRO_ALERT_HTTP_HEADERS_JSON` env var: `'{"example.com": {"Cookie": "session=abc"}}'`
- **Note:** Environment variable names use `PRO_ALERT_` prefix for historical reasons (original Patient Reported Outcomes use case), but they work with any Google Alert topic

### Summarization
- Requires local Ollama installation with `granite4:tiny-h` model pulled
- Model can be overridden via `--model` CLI flag or `PRO_ALERT_MODEL` env var
- Returns structured 4-bullet format: KEY FINDING, TACTICAL WIN [tag], MARKET SIGNAL [tag], CONCERN
- Digest includes executive summary and cross-article insights
- Works with any Google Alert topic—summaries adapt to content

### Mail Rule Automation (Recommended)
- Event-driven: processes alerts immediately when they arrive (any Google Alert topic)
- Mail rule conditions filter by From/Subject (e.g., `From: googlealerts-noreply@google.com`, `Subject: Google Alert -`)
- AppleScript (`process-pro-alert.scpt`) saves triggering message, runs Python pipeline, creates and sends HTML digest email
- Fully automated: alert arrival → digest generation → email delivery with no manual intervention
- Code is topic-agnostic—Mail rule conditions do ALL filtering
- See `Summarizer/MAIL_RULE_SETUP.md` for configuration details

### Cron Scheduling (Alternative)
- Wrapper script: `Summarizer/bin/run_pro_alert.sh`
- Configuration via `~/.pro-alert-env` (sourced by cron)
- Example crontab entry: `0 7 * * 1-5 /bin/bash -lc 'source ~/.pro-alert-env; /Users/you/Code/AppletScriptorium/Summarizer/bin/run_pro_alert.sh'`
- Environment variables (work with any Google Alert topic):
  - `PRO_ALERT_EMAIL_RECIPIENT` — failure notification address
  - `PRO_ALERT_NOTIFY_ON_SUCCESS=1` — enable success notifications
  - `PRO_ALERT_DIGEST_EMAIL` — comma-separated digest recipients
  - `PRO_ALERT_EMAIL_SENDER` — Mail.app account for sending
  - `PRO_ALERT_OUTPUT_DIR`, `PRO_ALERT_MODEL`, `PRO_ALERT_MAX_ARTICLES` — behavior tuning
  - **Note:** Variable names use `PRO_ALERT_` prefix for historical reasons but work with any Google Alert topic

## Coding Conventions

- **Python**: PEP 8, 4-space indents, snake_case for functions/variables
- **Scripts**: kebab-case filenames (e.g., `fetch-alert.scpt`)
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
