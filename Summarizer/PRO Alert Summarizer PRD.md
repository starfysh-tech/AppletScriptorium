### Project: AppletScriptorium — PRO Alert Summarizer (Phase 1)

#### Overview & Goals

* Automate the summarization of Google Alert emails (specifically for “Patient Reported Outcomes / PRO” topic) in Mail.app.
* For each alert email, extract article links, fetch article content, call an LLM to generate a structured summary, then send a digest email with clickable links and summaries.
* The user should receive a polished summary email without manual clicking, reading, or copying.
* The system should be robust: skip failures, avoid duplicates, support retries, and be maintainable.

#### Key Features & Workflow

| Step                         | Description                                                                                                                                                                          |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Email Trigger                | Mail.app rule triggers a script when a matching alert arrives (by subject).                                                                                                          |
| Fetch Email Source           | AppleScript fetches the full raw `source` (headers + HTML) of the triggered email.                                                                                                   |
| Parse Links                  | A helper script (e.g. Python or shell) extracts `<a href>` links + titles, unwraps Google redirect wrappers, filters only relevant article links.                                    |
| Fetch Articles               | For each link, perform HTTP fetch following redirects to retrieve full HTML.                                                                                                         |
| Summarize                    | Call LLM API with the fetched article content (or trimmed version) using a controlled prompt, get back summary output.                                                               |
| Postprocess Summary          | Parse and sanitize the LLM output (e.g. strip HTML wrapper, extract bullet points).                                                                                                  |
| Compose Digest               | Build an HTML digest email body that lists each article as a clickable title + bullet summary. Optionally prepend a short top-level summary.                                         |
| Send Email                   | Use AppleScript (`osascript`) to compose and send the digest email with HTML content via Mail.app.                                                                                   |
| Logging & Idempotency        | Record which alert emails (via message IDs) have been processed to avoid duplication. Log errors and successes.                                                                      |
| Error Handling & Concurrency | Each article fetch / summarize should be isolated so failures don’t abort entire flow. Use file locking or similar to prevent race conditions when multiple scripts run in parallel. |

#### Non-Goals (for Phase 1)

* Persistence to Google Sheets or database
* Parallel or batched bulk processing (beyond basic concurrency protection)
* Advanced fallback for JS-only article rendering (unless required)
* UI / GUI — this is fully script / background automation

#### Dependencies & Environment

* macOS (user’s laptop)
* Apple Mail app (with scripting enabled)
* `osascript` / AppleScript
* Shell scripting (bash / zsh)
* Python 3 (for HTML parsing, LLM calls)
* Access to an LLM API (e.g. OpenAI)
* Optional: HTML parsing library (BeautifulSoup)
* Optional: Readability / article text extraction library

#### Directory Structure

```
AppletScriptorium/
  scripts/
    fetch_alert.scpt
    send_digest.scpt
    master.sh
    parse_alert.py
    summarize_article.py
  logs/
  processed_ids.txt
  README.md
  config.json
```

* `scripts/`: AppleScript and shell/Python scripts
* `logs/`: logs of runs, errors
* `processed_ids.txt`: flat file storing processed email message IDs
* `config.json`: configuration (e.g. LLM keys, recipient address, subject filters)
* `README.md`: instructions, setup, usage

#### Configurable Parameters

* Email subject filter (e.g. “Google Alert – PRO”)
* Recipient email address
* LLM model name / API key
* Prompt template or formatting rules
* Timeouts, retry counts
* Lock file path
* Logging level

#### Error Handling / Edge Cases

* If link extraction fails (no links), skip and log
* If HTTP fetch fails or returns no content, skip that article
* If LLM API errors (timeout, rate limit), retry (up to N times), then skip
* If AppleScript sending fails, log and maybe retry once
* Use a lock (e.g. `flock` or PID lock file) to prevent concurrent runs racing
* On script start, check for existence of lock; if locked, abort or wait

#### Logging & Monitoring

* Log every run: timestamp, alert message ID, number of links, successfully summarized count
* Log per-article results: URL, summary text or error
* Log errors with stack traces or diagnostic data
* Optionally email you a failure report

#### Success Criteria & Test Cases

* On arrival of a sample alert email, the system sends you one summary email with clickable links and correct bullet summaries.
* Duplicate alert emails are not reprocessed.
* If one article fails, others still get processed.
* HTML formatting survives in the outgoing email.
* The system recovers gracefully from errors (timeouts, missing content).

#### Roadmap / Next Phases

* Support fallback rendering for JS-only pages (via headless browser)
* Store summaries persistently (database, spreadsheet)
* Add web dashboard / UI for reviewing summaries
* Support alerts on other topics (configurable)
* Add scheduling / batching / rate limits
