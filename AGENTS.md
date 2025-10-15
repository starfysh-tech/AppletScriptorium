# Project Overview

AppletScriptorium is a macOS automation framework using AppleScript, shell scripts, and Python. The first agent, **Summarizer**, processes Google Alert emails: extracts links, fetches articles, summarizes with local LLM (Ollama), and generates email digests. Build the simplest solution that works on local macOS—avoid premature abstractions.

## Build and Test Commands

### Prerequisites
- Python 3.11+ system Python (venv NOT supported—see Constraints below)
- Ollama with `qwen3:latest` model
- Mail.app configured

### Development Commands
```bash
# Run full pipeline (use -m for module invocation)
python3 -m Summarizer.cli run --output-dir runs/test --max-articles 3

# Run all tests
python3 -m pytest Summarizer/tests

# Run specific test file
python3 -m pytest Summarizer/tests/test_link_extractor.py -v

# Parse alert and view extracted links
python3 Summarizer/clean-alert.py Summarizer/Samples/google-alert-sample-2025-10-06.eml | head

# Refresh fixtures after parser changes
Summarizer/refresh-fixtures.py

# Validate AppleScript syntax before committing
osascript -s Summarizer/templates/process-alert.scpt
```

### Testing Instructions
- Run `python3 -m pytest Summarizer/tests` before every commit
- Fixtures in `Summarizer/Samples/` anchor regression tests
- After modifying parsers, run `Summarizer/refresh-fixtures.py` and diff output
- Mock external calls: `article_fetcher.clear_cache()` resets in-memory cache between tests
- For AppleScript changes, provide manual test steps or usage examples

## Code Style Guidelines

### Python
- PEP 8: 4-space indents, snake_case for functions/variables
- **Always** use module invocation: `python3 -m Summarizer.cli` (NOT `python3 Summarizer/cli.py`)
- Reason: Relative imports (`from .article_fetcher import ...`) require package mode
- Prefer pure functions and dependency injection for testability

### AppleScript
- Tab indentation (NOT spaces)
- Kebab-case filenames (e.g., `fetch-alert-source.applescript`)
- Include header comments describing trigger conditions and dependencies
- Validate syntax: `osascript -s <file>`

### Scripts
- Make shell scripts executable: `chmod +x`
- Provide usage examples in README or comments

## Project Structure

```
Summarizer/                    # Each agent in own directory
├── cli.py                     # Main orchestrator (invoke with -m)
├── config.py                  # Configuration constants (model, timeouts, domains)
├── link_extractor.py          # extract_links(eml_path) → list of dicts
├── article_fetcher.py         # fetch_article(url) → str (HTML/Markdown) + get_last_fetch_outcome()
├── content_cleaner.py         # extract_content(html) → Markdown
├── summarizer.py              # summarize_article(dict) → summary
├── digest_renderer.py         # render_digest_html/text(summaries)
├── fetch-alert-source.applescript  # Manual inbox capture
├── templates/process-alert.scpt    # Mail rule automation
├── Samples/                   # Committed fixtures for regression tests
│   ├── google-alert-sample-2025-10-06.eml
│   ├── google-alert-sample-2025-10-06-links.tsv
│   └── articles/              # Sample HTML for testing
└── tests/                     # Pytest suite
```

Future agents live alongside `Summarizer/`. Shared utilities migrate to `shared/` when needed.

## Critical Constraints

### System Python Requirement
- **Mail rule automation CANNOT use virtual environments**
- Mail.app scripts run in restricted sandbox without venv access
- **Must** install packages with `--user` flag: `python3 -m pip install --user -r requirements.txt`
- Packages install to `~/.local/lib/python3.x/site-packages`

### AppleScript Limitations
- Cannot activate venv (Mail.app sandbox restriction)
- Must use system Python: `which python3` (now dynamic for Intel/Apple Silicon compatibility)
- Tab indentation required (not spaces)
- Validate syntax before committing: `osascript -s <file>`

### Module Invocation Pattern
- **Always** use: `python3 -m Summarizer.cli run`
- **Never** use: `python3 Summarizer/cli.py`
- Reason: Package imports (`from .module import ...`) fail without `-m`

### Parallel Processing
- Uses `ThreadPoolExecutor` with max 5 workers for article fetch/summarize
- Pattern: `concurrent.futures.as_completed()` for progress tracking
- See `cli.py` lines 150-180 for reference

## Commit and PR Guidelines

### Commit Messages
- Imperative subjects <60 chars: `summarizer: add link parser`
- No emoji unless user explicitly requests

### Pull Requests
- Title format: `<scope>: <description>`
- List validation steps and attach relevant artifacts
- Reference issues/roadmap bullets
- Note new dependencies or env var requirements

### Before Committing
```bash
# Run tests
python3 -m pytest Summarizer/tests

# Validate AppleScript syntax
osascript -s Summarizer/templates/process-alert.scpt

# Check fixtures if parser changed
Summarizer/refresh-fixtures.py
diff -u Summarizer/Samples/google-alert-sample-2025-10-06-links.tsv /tmp/alert-links.tsv
```

## Security Considerations

- Never commit production emails, API keys, or Mail credentials
- Keep fixtures sanitized and redacted
- Use `.env` files (git-ignored) for secrets
- Document required env vars in README before merging
- Custom HTTP headers: `ALERT_HTTP_HEADERS_JSON='{"example.com": {"Cookie": "session=abc"}}'`

## Common Gotchas

- **PYTHONPATH**: Only set in shell wrappers for inline scripts; NOT needed for `-m` invocation
- **Markdown fallbacks**: `urltomd_fetcher.py` + `jina_fetcher.py` provide Markdown when httpx is blocked
- **Fixture regeneration**: Must diff against committed fixtures before merging parser changes
- **System permissions**: Different modes require different permissions:
  - **Mail rule automation**: Accessibility (System Settings → Privacy & Security → Accessibility → enable Mail.app)
  - **Manual CLI usage**: Automation (System Settings → Privacy & Security → Automation → enable Terminal → Mail)
- **Breaking changes**: No backward compatibility maintained—document in release notes only

## Additional Context

See `CLAUDE.md` for detailed development patterns, file reference map, and technical constraints.

## Development Principles

- Simple solutions over premature abstractions
- Production-ready code: logging, error handling, idempotency
- Document assumptions inline or in PRD
- Breaking changes documented in release notes only
