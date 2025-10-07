### Project: AppletScriptorium — PRO Alert Summarizer (Phase 1)

#### Overview & Goals
* Automate handling of Google Alert emails for the “Patient Reported Outcome” topic, anchored on the alert received by randall@mqol.com on **Mon, 06 Oct 2025 at 09:12 ET** (subject `Google Alert - “Patient reported outcome”`).
* Transform each alert into a polished digest: extract links, pull article content, generate concise bullet summaries, and output HTML suitable for Mail.app delivery.
* Deliver the solution incrementally so each layer is reliable before integrating the next.

#### Target Email Reference
* Sample `.eml`: `Summarizer/Google Alert - “Patient reported outcome”.eml`
* Expected HTML export: `Summarizer/alert.html`
* Stored artifacts (link lists, HTML snapshots) are the regression fixtures for ongoing development.

#### Current Repository Layout
```
AppletScriptorium/
  AGENTS.md
  README.md
  Summarizer/
    clean-alert.py
    fetch-alert-source.applescript
    refresh-fixtures.py
    requirements.txt
    Samples/
      google-alert-patient-reported-outcome-2025-10-06.eml
      google-alert-patient-reported-outcome-2025-10-06.html
      google-alert-patient-reported-outcome-2025-10-06-links.tsv
    PRO Alert Summarizer PRD.md
    ...additional fixtures...
```
* Each agent lives in its own top-level directory (Phase 1 only has `Summarizer/`).
* Future shared helpers will move into `shared/` once multiple agents depend on them.

#### Core Workflow Vision
1. Apple Mail rule forwards matching alerts into the Summarizer pipeline.
2. Parser extracts canonical article metadata from the alert payload.
3. Fetcher retrieves article HTML (with caching & retry guards).
4. Cleaner distills readable text from each article.
5. Summarizer (LLM or rule-based fallback) produces bullet highlights.
6. Digest assembler creates an HTML email fragment ready for Mail.app delivery.
7. Orchestrator logs results, skips already-processed alerts, and emits errors without halting the run.

#### Incremental Delivery Plan
Maintain the following checklist; update status and supporting docs after you confirm a task is complete.

- [x] **0. Scaffolding & Bootstrap** – Confirmed agent structure, added `Summarizer/requirements.txt`, and shipped `fetch-alert-source.applescript` plus README notes so the latest Mail alert source can be captured locally.
- [x] **1. Ground Truth Fixtures** – Regenerated the 09:12 alert fixtures (`google-alert-patient-reported-outcome-2025-10-06.*`), captured the decoded HTML plus link TSV via `refresh-fixtures.py`, and updated docs so contributors can rebuild and diff the baseline.
- [x] **2. Robust Link Extraction** – Introduced `link_extractor.py` with `.eml`/`.html` support, unwrapped Google redirects, wired the CLI via `clean-alert.py`, and added pytest coverage against the 09:12 fixtures.
- [x] **3. Metadata & Deduping Layer** – Extraction now captures publisher/snippet metadata, dedupes by canonical URL, emits TSV+JSON fixtures, and documentation outlines the schema and validation flow.
- [x] **4. Article Fetching Adapter** – Shipped `article_fetcher.py` with httpx-based retries, in-memory cache, JSON stub manifest support, and pytest coverage with mocked transports; requirements now list httpx.
- [x] **5. Content Extraction & Cleanup** – Added `content_cleaner.py` with readability-backed parsing (falling back gracefully), produces JSON content blocks, and tests cover the sample article fixture; README documents usage.
- [x] **6. Summary Generation Pipeline** – Introduced `summarizer.py` with an Ollama-backed runner (granite4:tiny-h), pluggable stubs for tests, JSON bullet output, and documentation covering setup/usage.
- [x] **7. Digest Assembly** – `digest_renderer.py` now emits HTML + plaintext digests, with tests and sample outputs; ready to feed downstream mailers.
- [x] **8. Automation & CLI Wrapper** – Added `Summarizer/cli.py` with `python3 -m Summarizer.cli run --output-dir …`, integrates the full pipeline with logging and README coverage.
- [x] **9. Deployment & Scheduling Prep** – Added cron-ready `Summarizer/bin/run_pro_alert.sh`, notification hooks, and deployment guidance in README/PRD.

#### Dependencies & Environment
* macOS with Apple Mail (scriptable), Python 3.11+, BeautifulSoup, readability library, HTTP client (requests/httpx).
* LLM access (e.g., OpenAI API) via environment-configured keys.
* Optional: local cache directory for fetched HTML, `.env` for secrets. Prefer lightweight local files over external services unless absolutely required.

#### Configurable Parameters
* Subject filter (`Google Alert - “Patient reported outcome”`).
* Output recipients, sender identity, and digest subject.
* Fetch timeouts/retries, cache TTL, dedupe window.
* LLM model, temperature, token budget, prompt templates.
* Logging level and lock file path.

#### Error Handling & Idempotency
* Guard every pipeline stage with retries and per-article isolation.
* Use message-ID tracking (flat file or SQLite) to skip already-processed alerts.
* Gracefully degrade: if article fetch or summarization fails, skip with clear logging while continuing others.
* Employ file locks to prevent parallel runs from colliding.

#### Logging & Monitoring
* Structured log lines per alert: message ID, link count, summary success/fail counts.
* Per-article diagnostics (URL, fetch status, summary status).
* Optional notification channel (email/slack) for failures.

#### Success Metrics
* The 09:12 alert processes end-to-end with accurate link extraction, cleaned content, and digest HTML ready to send.
* Additional alerts run without manual tweaks, respecting dedupe and error-handling rules.
* Automated regression (using stored fixtures + mocks) passes before deploy.

#### Future Extensions
* Some publishers (ASCO Daily News, ASH, Wiley, UroToday) currently return HTTP 403; plan a fetcher enhancement (browser fallback or cached fixture) to recover those links.
* Headless browser fallback for JS-heavy sites.
* Persistent storage (database, Sheets) for summaries.
* Multi-topic support via configuration.
* Integration with scheduler/orchestrator and broader AppletScriptorium agent suite.
