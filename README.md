# AppletScriptorium — Summarizer Module

AppletScriptorium is a collection of macOS automation agents orchestrated through AppleScript, shell, and Python helpers. The first agent, **Summarizer**, watches Mail.app for Google Alerts, extracts article links, fetches pages, summarizes them with a local LLM, and generates intelligent digest emails.

## Quick Start

**New to AppletScriptorium?** See the complete setup guide: **[SETUP.md](./SETUP.md)**

```bash
cd ~/Code
git clone https://github.com/yourusername/AppletScriptorium.git
cd AppletScriptorium
./install.sh           # Automated setup (prereqs, dependencies, model)
./setup-mail-rule.sh   # Configure Mail rule automation (interactive)
./validate.sh          # Verify installation
```

**Troubleshooting?** See **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)**

---

## Repository Structure

```
.
├── AGENTS.md                     # AI assistant guidelines (Codex, Gemini, etc.)
├── CLAUDE.md                     # Claude Code development guide
├── Summarizer/                   # Google Alert Intelligence agent
│   ├── config.py                 # Configuration constants
│   ├── cli.py                    # Main orchestrator
│   ├── link_extractor.py         # Extract links from alert emails
│   ├── article_fetcher.py        # HTTP fetcher with Playwright fallback
│   ├── content_cleaner.py        # HTML to Markdown conversion
│   ├── summarizer.py             # LLM summarization
│   ├── digest_renderer.py        # HTML/text digest generation
│   ├── fetch-alert-source.applescript  # Manual alert capture
│   ├── templates/process-alert.scpt    # Mail rule automation
│   ├── requirements.txt          # Python dependencies
│   ├── Samples/                  # Fixtures for regression tests
│   └── tests/                    # Pytest suite
├── SETUP.md                      # Installation guide
├── TROUBLESHOOTING.md            # Common issues and solutions
└── README.md                     # This file
```

Future agents will live alongside `Summarizer/`. Shared utilities will migrate to `shared/` when needed.

---

## Usage

### Mail Rule Automation (Recommended)

Event-driven processing triggered when Google Alerts arrive:

1. Run `./setup-mail-rule.sh` to install AppleScript
2. Create Mail rule:
   - **From**: `googlealerts-noreply@google.com`
   - **Subject**: `Google Alert -`
   - **Action**: Run AppleScript → `process-alert.scpt`
3. Grant Accessibility permissions (System Settings → Privacy & Security → Accessibility → Mail.app)

**Workflow:**
Alert arrives → Mail rule triggers → Pipeline runs → Digest email sent automatically

See **[SETUP.md](./SETUP.md)** for detailed configuration.

### CLI

Run the full pipeline (fetch, summarize, generate digest):

```bash
# Process most recent Google Alert
python3 -m Summarizer.cli run \
  --output-dir runs/manual-$(date +%Y%m%d-%H%M%S) \
  --subject-filter "Google Alert -"

# Limit articles and send digest via email
python3 -m Summarizer.cli run \
  --output-dir runs/test \
  --max-articles 5 \
  --email-digest user@example.com \
  --email-sender user@example.com
```

**Configuration**: Defaults in `Summarizer/config.py`. Override via CLI flags or `ALERT_*` environment variables.

**Outputs**: `alert.eml`, `alert.tsv`, `articles/`, `digest.html`, `digest.txt`, `workflow.log`

**CLI Flags:**
- `--model MODEL` — Override Ollama model (default: qwen3:latest)
- `--max-articles N` — Limit articles processed
- `--email-digest ADDRESS` — Send digest via Mail.app (repeatable)
- `--email-sender ADDRESS` — Select Mail.app sender account
- `--subject-filter PATTERN` — Match specific inbox messages

### Cron Scheduling

For fixed-schedule digests instead of event-driven processing:

1. Create `~/.alert-env` with configuration
2. Add cron job: `crontab -e`
   ```cron
   0 7 * * 1-5 /bin/bash -lc 'source ~/.alert-env; /path/to/Summarizer/bin/run_alert.sh'
   ```

See **[SETUP.md](./SETUP.md)** for cron configuration details.

---

## Testing

```bash
# Run all tests
python3 -m pytest Summarizer/tests

# Run specific test
python3 -m pytest Summarizer/tests/test_link_extractor.py -v
```

---

## Development

- **For Claude Code**: See **[CLAUDE.md](./CLAUDE.md)** for development commands, code style, and module patterns
- **For other AI assistants**: See **[AGENTS.md](./AGENTS.md)** for build commands and project conventions
- **Configuration**: Edit `Summarizer/config.py` for model, timeouts, parallelism, domain lists

**Key technical details:**
- System Python required (no venv support for Mail rules)
- Module invocation: `python3 -m Summarizer.cli` (NOT `python3 Summarizer/cli.py`)
- Parallel processing: ThreadPoolExecutor with max 5 workers (~70% faster)
- Fixture management: `Summarizer/refresh-fixtures.py`

---

## Support

- **Setup issues**: [SETUP.md](./SETUP.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- **Development**: [CLAUDE.md](./CLAUDE.md) or [AGENTS.md](./AGENTS.md)
- **Logs**: `runs/*/workflow.log`
