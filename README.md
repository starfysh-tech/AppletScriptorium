# AppletScriptorium — Summarizer Module

AppletScriptorium is a collection of macOS automation agents orchestrated through AppleScript, shell, and Python helpers. The first agent, **PRO Alert Summarizer**, watches Mail.app for Google Alerts about Patient Reported Outcomes, extracts article links, fetches the corresponding pages, summarizes them with an LLM, and prepares a digest email with clickable links.

## Working Agreement
- Ship the simplest solution that works on the local Mac; postpone abstractions until they become necessary.
- Treat every task as production-bound: add logging, thorough error handling, idempotency, and locking when parallel runs are possible.
- The maintainer will provide focused tasks (e.g., “write AppleScript to fetch message source”). For each task deliver the code, usage examples or tests, and clear inline comments for non-obvious choices.
- Ask clarifying questions only when requirements are unclear; otherwise proceed with best-practice defaults documented here and in the PRD.

## Repository Structure (current)
```
.
├── AGENTS.md                     # Contributor guidelines & workflow expectations
├── Summarizer/                   # PRO Alert Summarizer agent (fixtures + scripts)
│   ├── article_fetcher.py        # Minimal HTTP fetcher with retries
│   ├── clean-alert.py            # Link extraction CLI wrapper
│   ├── content_cleaner.py        # Converts article HTML into Markdown text
│   ├── fetch-alert-source.applescript  # Mail helper to pull raw alert source
│   ├── refresh-fixtures.py       # Helper to rebuild committed samples
│   ├── requirements.txt          # Python dependencies for the agent
│   ├── Samples/
│   │   ├── google-alert-patient-reported-outcome-2025-10-06.eml
│   │   ├── google-alert-patient-reported-outcome-2025-10-06.html
│   │   ├── google-alert-patient-reported-outcome-2025-10-06-links.tsv
│   │   └── google-alert-patient-reported-outcome-2025-10-06-links.json
│   ├── Samples/articles/         # Sample fetched article HTML for cleaning
│   └── PRO Alert Summarizer PRD.md
├── LICENSE
└── README.md
```
Future agents (Mailer, Orchestrator, etc.) will live alongside `Summarizer/`. Shared utilities will migrate into a top-level `shared/` package once more than one agent depends on them.

## Getting Started
1. Create a virtual environment: `python3 -m venv .venv && source .venv/bin/activate`.
2. Install Python dependencies for the agent: `python3 -m pip install -r Summarizer/requirements.txt`.
3. Refresh the raw alert fixture (safe to overwrite the committed file):
   ```bash
   osascript Summarizer/fetch-alert-source.applescript Summarizer/Samples/google-alert-patient-reported-outcome-2025-10-06.eml
   ```
4. Regenerate the decoded HTML body and expected link list:
   ```bash
   Summarizer/refresh-fixtures.py
   ```
5. Inspect the parsed output on the command line (TSV by default):
   ```bash
   python3 Summarizer/clean-alert.py Summarizer/Samples/google-alert-patient-reported-outcome-2025-10-06.eml | head
   ```
6. Emit JSON instead when you need structured metadata:
   ```bash
   python3 Summarizer/clean-alert.py --format json | jq '.' | head
   ```
7. When the parser changes, rebuild scratch artifacts and diff against the fixtures:
   ```bash
   Summarizer/refresh-fixtures.py --links /tmp/alert-links.tsv --links-json /tmp/alert-links.json --html /tmp/alert.html
   diff -u Summarizer/Samples/google-alert-patient-reported-outcome-2025-10-06-links.tsv /tmp/alert-links.tsv
   diff -u Summarizer/Samples/google-alert-patient-reported-outcome-2025-10-06-links.json /tmp/alert-links.json
   ```
8. Refer to `Summarizer/PRO Alert Summarizer PRD.md` for the staged roadmap (fixtures → link extraction → fetcher → summarizer → digest).

The AppleScript searches the Inbox for the newest message whose subject begins with `Google Alert -` and contains `Patient reported outcome`. Update the `subject_prefix` and `topic_keyword` variables in `Summarizer/fetch-alert-source.applescript` if your alerts land in a different format or mailbox.

## Article Fetching
- Use `Summarizer/article_fetcher.py` in scripts or REPL sessions to retrieve article HTML.
- Provide extra headers (cookies, auth tokens) by exporting `PRO_ALERT_HTTP_HEADERS_JSON`, e.g. `'{"example.com": {"Cookie": "session=abc"}}'`.
- The fetcher caches responses in-memory for the life of the process; call `article_fetcher.clear_cache()` in tests to reset state.
- For Cloudflare-guarded publishers (`dailynews.ascopubs.org`, `ashpublications.org`, `obgyn.onlinelibrary.wiley.com`, etc.) install Playwright so the headless fallback can render the page:
  ```bash
  python3 -m pip install playwright
  playwright install
  ```

## Content Extraction
- `Summarizer/content_cleaner.py` exposes `extract_content(html)` which returns Markdown text extracted from the readable portion of the page.
- Example usage with the sample article fixture:
  ```bash
  python3 - <<'PY'
  from pathlib import Path
  from content_cleaner import extract_content

  html = Path('Summarizer/Samples/articles/pro-diction-models.html').read_text(encoding='utf-8')
  markdown = extract_content(html)
  print(markdown.splitlines()[0])
  PY
  ```

## Summary Generation
- `Summarizer/summarizer.py` calls Ollama with the `granite4:tiny-h` model and returns structured bullet summaries.
- Ensure Ollama is installed locally and the model is pulled (`ollama pull granite4:tiny-h`).
- The fetcher automatically retries Cloudflare-guarded publishers with a Playwright-powered headless browser when available.
- Example invocation using the same sample article blocks (ensure Ollama is running locally):
  ```bash
  python3 - <<'PY'
  from pathlib import Path
  from content_cleaner import extract_content
  from summarizer import summarize_article

  html = Path('Summarizer/Samples/articles/pro-diction-models.html').read_text(encoding='utf-8')
  article = {
      "title": "From Prediction to PRO-Diction Models",
      "url": "https://example.com/article",
      "content": extract_content(html),
  }
  summary = summarize_article(article)
  print(summary)
  PY
  ```

## Digest Assembly
- `Summarizer/digest_renderer.py` generates both HTML and plaintext digests from the summary payloads.
- Sample outputs land in `Summarizer/Samples/articles/pro-diction-models.digest.*`.
- Integration example using the same sample summary:
  ```bash
  python3 - <<'PY'
  from pathlib import Path
  from digest_renderer import render_digest_html, render_digest_text

  summary = eval(Path('Summarizer/Samples/articles/pro-diction-models.summary.json').read_text())
  print(render_digest_text([summary]))
  html = render_digest_html([summary])
  Path('/tmp/digest.html').write_text(html)
  PY
  ```

## Testing
- `python3 -m pytest Summarizer/tests` validates link extraction, metadata, fetcher behaviour, and rendering against the committed fixtures.

## Development Expectations
- Keep fixtures sanitized; never commit production emails or secrets.
- Document new configuration requirements (subjects, env vars, API keys) in both README and PRD.
- Provide script usage samples or tests with each change. Pytest-based checks, mocked AppleScript invocations, or CLI dry runs are all acceptable until end-to-end automation is wired.
- When making simplifying assumptions, document them inline or in the PRD so future contributors know why a minimal approach was chosen.
- Ensure AppleScript and shell scripts are executable (`chmod +x script.scpt` or wrap in `.applescript` compiled via `osascript`). Include header comments describing triggers and dependencies.

## Roadmap Snapshot
The project proceeds incrementally:
1. Normalize fixtures for the 09:12 alert email.
2. Harden link extraction with decoding, redirect unwrapping, and tests.
3. Enrich metadata + dedupe, output structured JSON.
4. Build fetcher with retries/caching.
5. Extract readable article text.
6. Integrate summarizer (LLM with mockable interface).
7. Assemble HTML digest with snapshot tests.
8. Ship CLI/automation wrapper.
9. Prepare deployment hooks for Mail.app rules and scheduling.

See the PRD for detailed acceptance criteria and future extensions (JS rendering fallback, persistent storage, multi-topic support).

## CLI / Automation
- `python3 -m Summarizer.cli run --output-dir /path/to/run` runs the full pipeline (fetches latest alert, fetches articles, summarizes, renders digests). This now works without adjusting `PYTHONPATH`.
- Optional flags:
  - `--model MODEL` overrides the Ollama model (default: granite4:tiny-h).
  - `--max-articles N` limits how many stories to process.
  - `--email-digest ADDRESS` sends the plaintext digest via Mail.app to the given address (repeatable). You can also set `PRO_ALERT_DIGEST_EMAIL` with a comma-separated list to mirror this flag.
  - `--email-sender ADDRESS` explicitly selects the Mail.app account/address used when sending the digest. You can also set `PRO_ALERT_EMAIL_SENDER` to define a default.
- Outputs mirror `run_workflow.sh`: raw alert, TSV, article artifacts, HTML/plaintext digests, and `workflow.log`.
- Digests include a "Missing articles" section summarizing any URLs that failed to fetch or clean.
- When email delivery is enabled, the CLI drives Mail.app via AppleScript—messages appear in Outgoing/Sent like any manual mail. Provide a sender address (or rely on Mail’s default) that matches a configured account.
- Headless retries trigger automatically once Playwright is installed; see "Article Fetching" for setup instructions.

### Scheduling with cron
1. Set optional environment variables in `~/.pro-alert-env` (sourced by cron):
   - `PRO_ALERT_EMAIL_RECIPIENT` — address to notify on failure (requires `mail`).
   - `PRO_ALERT_NOTIFY_ON_SUCCESS=1` to also notify when runs succeed.
   - `PRO_ALERT_OUTPUT_DIR`, `PRO_ALERT_MODEL`, `PRO_ALERT_MAX_ARTICLES` tune destination/behavior.
   - `PRO_ALERT_DIGEST_EMAIL` — comma-separated recipients for the digest (equivalent to repeating `--email-digest`).
   - `PRO_ALERT_EMAIL_SENDER` — sender address to select the Mail.app account used for digests.
2. Add the job (edit with `crontab -e`):
   ```cron
   0 7 * * 1-5 /bin/bash -lc 'source ~/.pro-alert-env; /Users/you/Code/AppletScriptorium/Summarizer/bin/run_pro_alert.sh'
   ```
3. Logs/digests land under `runs/<timestamp>`, matching the CLI workflow.
4. To email the digest automatically, add
   ```bash
   PRO_ALERT_DIGEST_EMAIL="randall@mqol.com"
   PRO_ALERT_EMAIL_SENDER="randall@mqol.com"
   ```
   to `~/.pro-alert-env`. The wrapper expands these to the CLI flags at runtime.
