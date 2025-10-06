Here’s an updated README tailored to the fact that *summarizer* is the first script, and that the repo will host more automation scripts over time:

---

# AppletScriptorium — Summarizer Module

A macOS automation module in the **AppletScriptorium** suite. This module processes Google Alert emails (on Patient-Reported Outcomes) into a summarized newsletter email. Additional automation modules will live alongside it in the same repo.

## 📁 Repository Structure (current)

```
.
├── Summarizer/                      ← module folder
│   ├── alert-cleaned.txt
│   ├── alert.html
│   ├── clean-alert.py
│   ├── email-content.txt
│   ├── email-source.txt
│   ├── email-subject.txt
│   ├── Google Alert – “Patient reported outcome”.eml
│   ├── prediction-actual.html
│   ├── prediction.html
│   └── summary.html
├── LICENSE
└── README.md
```

* `Summarizer/` — the module that transforms alert emails into article summaries.
* In `Summarizer/`:

  * `clean-alert.py` — parses alert HTML to extract link titles & URLs.
  * `alert.html` / `.eml` / `email-source.txt` etc. — sample artifacts used for development & testing.
  * `prediction.html` / `prediction-actual.html` — sample fetched article HTMLs.
  * `summary.html` — sample output summarization (HTML) from the module.

Other modules (e.g. “Mailer”, “Scheduler”, “Archiver”) will be added at the top level as sibling directories under this repo.

## ✅ Module Purpose & Scope

This “Summarizer” module’s sole job is:

* Ingest a Google Alert email (via raw HTML or `.eml`)
* Extract links and titles from that alert
* (Future) Fetch each linked article’s HTML
* (Future) Call an LLM to generate structured bullet summaries
* (Future) Produce an HTML digest summarizing each article with clickable links

It does **not** yet send emails, manage locking, schedule itself, or persist state. Those responsibilities will live in other modules.

## 🧪 How to Test This Module Locally

1. Copy or export a Google Alert email’s raw HTML or `.eml` into `Summarizer/` (e.g. as `alert.html`).

2. Run the cleaning parser to extract links:

   ```bash
   cd Summarizer
   python3 clean-alert.py < alert.html > alert-cleaned.txt
   ```

   The output should be lines in the format:

   ```
   Article Title<TAB>Cleaned URL
   ```

3. Use sample `prediction.html` to simulate a fetched article. In a future version, generate summary HTML and compare it with `summary.html`.

## ⚙ Dependencies & Setup (for this module)

* Python 3

* Python packages (install via pip):

  ```
  pip install beautifulsoup4 requests
  ```

* Optionally, a readability / content extraction library for cleaning article HTML in the future.

* LLM API credentials (for when summarization is wired).

## 📌 Roadmap & Upcoming Modules

The repo will expand with modules such as:

* **Mailer** — compose and send the digest email via AppleScript / Mail.app
* **Fetcher** — robust logic to fetch article HTML, including fallback for JS pages
* **Supervisor / Orchestrator** — manage scheduling, locking, error retries, concurrency
* **Archiver / Logger** — persistent storage of processed alerts, logs, audit trail

Eventually, the full flow will be:

> Mail rule → Summarizer → Fetcher → Mailer → notify

## 🎯 Success Criteria for the Summarizer Module

* Given an alert HTML (or `.eml`), the `clean-alert.py` reliably extracts correct titles and clean URLs, unwrapping Google redirect wrappers
* Summarizer module can operate independently (does not depend on sending or external state)
* The extracted output matches expectations when tested against sample files (e.g. `alert.html`, `summary.html`)