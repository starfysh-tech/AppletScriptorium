# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AppletScriptorium is a macOS automation framework that uses AppleScript, shell scripts, and Python to build agents that automate local workflows. The first agent, **PRO Alert Summarizer**, monitors Mail.app for Google Alerts about Patient Reported Outcomes, extracts article links, fetches pages, summarizes them with a local LLM (Ollama), and generates email digests.

## Architecture

### Pipeline Flow
1. **Alert Capture** (`fetch-alert-source.applescript`) — AppleScript queries Mail.app for latest Google Alert
2. **Link Extraction** (`link_extractor.py`) — Parses email HTML, extracts article URLs with metadata
3. **Article Fetching** (`article_fetcher.py` + `crawlee_fetcher.py`) — HTTP fetcher with Playwright fallback for Cloudflare-protected sites
4. **Content Cleaning** (`content_cleaner.py`) — Converts HTML to readable Markdown using readability-lxml
5. **Summarization** (`summarizer.py`) — Calls local Ollama (granite4:tiny-h model) for structured bullet summaries
6. **Digest Rendering** (`digest_renderer.py`) — Generates HTML and plaintext email digests
7. **CLI Orchestration** (`cli.py`) — Ties all steps together with logging and error handling

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
# Refresh raw alert fixture (overwrites committed .eml)
osascript Summarizer/fetch-alert-source.applescript Summarizer/Samples/google-alert-patient-reported-outcome-2025-10-06.eml

# Rebuild decoded HTML and expected link list
Summarizer/refresh-fixtures.py

# Validate changes against committed fixtures
Summarizer/refresh-fixtures.py --links /tmp/alert-links.tsv --links-json /tmp/alert-links.json --html /tmp/alert.html
diff -u Summarizer/Samples/google-alert-patient-reported-outcome-2025-10-06-links.tsv /tmp/alert-links.tsv
```

### Running the Pipeline

#### CLI (preferred)
```bash
# Full pipeline with output to timestamped directory
python3 -m Summarizer.cli run --output-dir runs/$(date +%Y%m%d-%H%M%S)

# With article limit and custom model
python3 -m Summarizer.cli run --output-dir runs/test --max-articles 5 --model granite4:tiny-h

# Email digest to recipients
python3 -m Summarizer.cli run --output-dir runs/latest --email-digest randall@mqol.com --email-sender randall@mqol.com
```

#### Shell Wrapper (alternative)
```bash
# Run via bash script (creates timestamped directory in runs/)
./run_workflow.sh
```

### Quick Validation
```bash
# Parse alert and view links (TSV format)
python3 Summarizer/clean-alert.py Summarizer/Samples/google-alert-patient-reported-outcome-2025-10-06.eml | head

# Parse alert and view links (JSON format)
python3 Summarizer/clean-alert.py --format json Summarizer/Samples/google-alert-patient-reported-outcome-2025-10-06.eml | jq '.' | head
```

## Key Technical Details

### AppleScript Integration
- `fetch-alert-source.applescript` searches Mail.app Inbox for subject starting with "Google Alert -" containing "Patient reported outcome"
- Edit `subject_prefix` and `topic_keyword` variables in the script to match different alert formats
- AppleScript files must be executable or run via `osascript`

### Article Fetching Strategy
- Primary: httpx with user-agent headers
- Fallback: Crawlee + Playwright for Cloudflare-protected domains
- In-memory caching for the life of the process
- Custom headers via `PRO_ALERT_HTTP_HEADERS_JSON` env var: `'{"example.com": {"Cookie": "session=abc"}}'`

### Summarization
- Requires local Ollama installation with `granite4:tiny-h` model pulled
- Model can be overridden via `--model` CLI flag or `PRO_ALERT_MODEL` env var
- Returns structured JSON with title, key_points, and clinical_relevance fields

### Cron Scheduling
- Wrapper script: `Summarizer/bin/run_pro_alert.sh`
- Configuration via `~/.pro-alert-env` (sourced by cron)
- Example crontab entry: `0 7 * * 1-5 /bin/bash -lc 'source ~/.pro-alert-env; /Users/you/Code/AppletScriptorium/Summarizer/bin/run_pro_alert.sh'`
- Environment variables:
  - `PRO_ALERT_EMAIL_RECIPIENT` — failure notification address
  - `PRO_ALERT_NOTIFY_ON_SUCCESS=1` — enable success notifications
  - `PRO_ALERT_DIGEST_EMAIL` — comma-separated digest recipients
  - `PRO_ALERT_EMAIL_SENDER` — Mail.app account for sending
  - `PRO_ALERT_OUTPUT_DIR`, `PRO_ALERT_MODEL`, `PRO_ALERT_MAX_ARTICLES` — behavior tuning

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
