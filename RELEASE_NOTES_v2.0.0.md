# Release v2.0.0 — Google Alert Intelligence

**Release Date:** October 14, 2025

## Overview

First production release of **Google Alert Intelligence**, a macOS automation framework that monitors Mail.app for Google Alerts on any topic, fetches articles, summarizes them with local LLM (Ollama), and generates intelligent email digests.

This release includes:
- Automated setup scripts for new machines
- Mail rule automation for event-driven processing
- Parallel article processing (~70% faster)
- Cloudflare/PerimeterX bypass with Playwright
- HTML email digest generation
- Comprehensive documentation

## 🚨 Breaking Changes

### Environment Variable Rename
**All environment variables have been renamed:**
- `PRO_ALERT_*` → `ALERT_*`

**No backward compatibility maintained.** The code only recognizes `ALERT_*` variables.

**Required actions:**
- Rename variables in `~/.alert-env`: `sed -i '' 's/PRO_ALERT_/ALERT_/g' ~/.alert-env`
- Update cron jobs to use `run_alert.sh` (not `run_pro_alert.sh`)
- Rename Mail AppleScript: `process-alert.scpt` (not `process-pro-alert.scpt`)

**Affected variables:**
- `ALERT_OUTPUT_DIR` (was `PRO_ALERT_OUTPUT_DIR`)
- `ALERT_MODEL` (was `PRO_ALERT_MODEL`)
- `ALERT_MAX_ARTICLES` (was `PRO_ALERT_MAX_ARTICLES`)
- `ALERT_DIGEST_EMAIL` (was `PRO_ALERT_DIGEST_EMAIL`)
- `ALERT_EMAIL_SENDER` (was `PRO_ALERT_EMAIL_SENDER`)
- `ALERT_EMAIL_RECIPIENT` (was `PRO_ALERT_EMAIL_RECIPIENT`)
- `ALERT_NOTIFY_ON_SUCCESS` (was `PRO_ALERT_NOTIFY_ON_SUCCESS`)
- `ALERT_HTTP_HEADERS_JSON` (was `PRO_ALERT_HTTP_HEADERS_JSON`)

### Script Renames
- `Summarizer/bin/run_pro_alert.sh` → `Summarizer/bin/run_alert.sh`
- `process-pro-alert.scpt` → `process-alert.scpt`

## ✨ Features

### Automated Setup
- **`install.sh`**: One-command setup for new machines (dependencies, Ollama model, tests)
- **`setup-mail-rule.sh`**: Interactive Mail rule configuration
- **`validate.sh`**: 10-step validation with progress indicators ([N/10] format)

### Mail Rule Automation (Recommended)
- Event-driven processing when Google Alerts arrive
- Works with ANY Google Alert topic
- Mail rule conditions handle all filtering
- Fully automated: alert arrival → digest generation → email delivery
- See `Summarizer/MAIL_RULE_SETUP.md` for setup

### Performance
- **Parallel processing**: Max 5 concurrent workers via ThreadPoolExecutor
- **~70% faster** than sequential processing
- In-memory caching for fetched articles

### Article Fetching
- Primary: httpx with custom headers support
- Fallback: Crawlee + Playwright for Cloudflare/PerimeterX-protected sites
- Automatic retry with exponential backoff
- Domains supported: dailynews.ascopubs.org, ashpublications.org, urotoday.com, jacc.org, medrxiv.org, PMC, Wiley, ScienceDirect, news10.com
- Custom headers via `ALERT_HTTP_HEADERS_JSON` for authenticated sites

### Summarization
- Local Ollama integration (granite4:tiny-h model)
- Structured 4-bullet format: KEY FINDING, TACTICAL WIN, MARKET SIGNAL, CONCERN
- Executive summary across all articles
- Cross-article insights

### Digest Rendering
- **HTML output**: Rich formatting, bold labels, visual hierarchy
- **Plaintext output**: Email-friendly text format
- **MIME .eml files**: For Mail.app integration
- Missing articles section with failure reasons

### CLI
```bash
python3 -m Summarizer.cli run \
  --output-dir runs/test \
  --max-articles 5 \
  --model granite4:tiny-h \
  --email-digest user@example.com \
  --email-sender user@example.com \
  --subject-filter "Google Alert -"
```

### Cron Scheduling (Alternative)
- `Summarizer/bin/run_alert.sh` wrapper for scheduled runs
- Configuration via `~/.alert-env`
- macOS notifications on success/failure
- See `Summarizer/deploy/README.md`

## 📚 Documentation

### Setup Guides
- **`SETUP.md`**: Complete setup for new machines (automated + manual)
- **`MAIL_RULE_SETUP.md`**: Mail rule automation configuration
- **`README.md`**: Quick start and feature overview
- **`CLAUDE.md`**: Development commands and architecture

### Key Documentation
- Works with ANY Google Alert topic (not just Patient Reported Outcomes)
- Mail rule conditions do ALL filtering (no hardcoded subjects)
- System Python required for Mail rules (no virtual environment)
- Playwright required for Cloudflare-protected sites

## 🔧 Installation

### Quick Install (3 commands)
```bash
cd ~/Code
git clone https://github.com/yourusername/AppletScriptorium.git
cd AppletScriptorium
./install.sh           # Automated setup
./setup-mail-rule.sh   # Configure Mail rule
./validate.sh          # Verify installation
```

### Prerequisites
- macOS 12.0+ (tested on 15.6.1)
- Python 3.11+
- Homebrew
- Ollama
- Mail.app configured with email account

## 🧪 Testing

- **21 test cases** covering link extraction, article fetching, content cleaning, summarization, digest rendering, CLI integration
- Run: `python3 -m pytest Summarizer/tests -v`
- All tests passing ✓

## 📦 What's Included

### Core Modules
- `link_extractor.py`: Parses Google Alert emails, extracts article URLs with metadata
- `article_fetcher.py`: HTTP fetcher with Cloudflare fallback
- `crawlee_fetcher.py`: Playwright-based headless browser for protected sites
- `content_cleaner.py`: HTML → Markdown conversion with readability-lxml
- `summarizer.py`: Ollama integration with structured output
- `digest_renderer.py`: HTML and plaintext digest generation
- `cli.py`: CLI orchestration with parallel processing

### Scripts
- `fetch-alert-source.applescript`: Captures inbox messages (manual CLI)
- `process-alert.scpt`: Mail rule automation script (Mail.app)
- `run_alert.sh`: Cron wrapper for scheduled runs
- `clean-alert.py`: Standalone link extraction utility

### Fixtures
- `Samples/google-alert-sample-2025-10-06.eml`: Sample alert email
- `Samples/articles/*.html`: Sample fetched articles
- Used for regression testing

## 🐛 Bug Fixes

- Fixed validate.sh exiting early on first failure (removed `set -e`)
- Fixed Crawlee event loop conflicts with asyncio
- Fixed PerimeterX challenge handling
- Fixed Mail.app HTML rendering with MIME .eml approach

## 📈 Performance Metrics

- **Parallel processing**: ~70% faster with 5 workers vs sequential
- **Article fetch**: 2-10s per article (httpx), 13-18s (Crawlee fallback)
- **Summarization**: ~5-10s per article (granite4:tiny-h)
- **End-to-end**: 5-10 articles in ~2-3 minutes

## 🔮 Limitations

- macOS only (uses AppleScript, Mail.app)
- Requires local Ollama installation
- Mail rule automation requires system Python (no venv)
- Cloudflare fallback requires Playwright browsers (~200MB)

## 🛠️ Development

### Contributing
- See `CLAUDE.md` for development guidelines
- Run tests before committing: `python3 -m pytest Summarizer/tests`
- Follow conventional commits format

### Architecture
- Each agent in top-level directory (currently `Summarizer/`)
- Fixtures in `Samples/` for regression testing
- Shared utilities migrate to `shared/` when multiple agents need them

## 🔗 Links

- **Documentation**: See SETUP.md, README.md, MAIL_RULE_SETUP.md
- **PRD**: See Summarizer/PRO Alert Summarizer PRD.md (documents original use case)

## 🙏 Acknowledgments

Built with Claude Code (claude.com/code).

---

**Full Changelog**: https://github.com/yourusername/AppletScriptorium/commits/v2.0.0
