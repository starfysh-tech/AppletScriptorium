# Deployment Guide — Google Alert Intelligence

This repository ships the tooling and scripts needed to capture Google Alerts (any topic), fetch the linked articles, summarize them with LM Studio, and emit HTML/text digests with optional Ollama fallback.

## Deployment Options

**Recommended: Mail Rule Automation (Event-Driven)**
For real-time processing when Google Alerts arrive, see [`../../docs/SETUP.md#mail-rule-automation`](../../docs/SETUP.md#mail-rule-automation) for complete Mail.app rule configuration. This provides immediate processing with no cron scheduling needed.

**Alternative: Cron Scheduling (Time-Based)**
To run the pipeline on a fixed schedule from your Mac, follow the steps below. This is useful for batch digest generation but lacks the real-time responsiveness of Mail rules.

## 1. Prerequisites

- **Python 3.11+**
- **Apple Mail** with script support enabled (for AppleScript to fetch the alert)
- **LM Studio** running with a loaded model
- **Ollama** optional fallback backend (`brew install ollama` and `ollama pull qwen3:latest` if you enable it)

Install Python dependencies once:
```bash
python3 -m pip install --user -r Summarizer/requirements.txt
```

## 2. Test the Pipeline Manually

From the repo root, generate a full run to ensure everything works:
```bash
# Process most recent inbox message
python3 -m Summarizer.cli run --output-dir runs/manual-test

# Or specify a subject filter to match specific alerts
python3 -m Summarizer.cli run \
  --output-dir runs/manual-test \
  --subject-filter "Medication reminder"
```

**Performance:** Articles are processed in parallel (max 5 concurrent workers), typically reducing execution time by ~70% compared to sequential processing.

This creates:
- `runs/manual-test/alert.eml` (raw email)
- `.../alert.tsv` (link metadata)
- `.../articles/` (fetched HTML, cleaned content, summaries)
- `.../digest.html` / `digest.txt`
- `.../workflow.log`

## 3. Wrapper Script

`Summarizer/bin/run_alert.sh` wraps the CLI for cron/automation. It:
- Sets `PYTHONPATH`
- Chooses an output dir (default `runs/<timestamp>`, overridable via `ALERT_OUTPUT_DIR`)
- Executes the CLI
- Sends macOS notifications (and optional log email using `mail`)

Optional environment variables (set in `~/.alert-env`):
- `ALERT_EMAIL_RECIPIENT` — notify on failures
- `ALERT_NOTIFY_ON_SUCCESS=1` — also notify when runs succeed
- `ALERT_OUTPUT_DIR` — override the default output directory
- `ALERT_MODEL`, `ALERT_MAX_ARTICLES` — tune behavior
- `ALERT_DIGEST_EMAIL` — comma-separated recipients; the CLI uses these to create `digest.eml`
- `ALERT_EMAIL_SENDER` — optional `From` header for generated digest messages and SMTP sends

## 4. Cron Setup

1. Create `~/.alert-env` and export any of the variables above (or copy from `Summarizer/templates/alert-env.template`).
2. Add the cron entry:
   ```cron
   0 7 * * 1-5 /bin/bash -lc 'source ~/.alert-env; /Users/<you>/Code/AppletScriptorium/Summarizer/bin/run_alert.sh'
   ```
3. Confirm with `crontab -l`.

## 5. Logs & Monitoring

- Each run writes to `runs/<timestamp>/workflow.log`.
- Notifications include basic status; full detail is in the log.
- Failures typically imprint the last HTTP status or summarizer error.

## 6. Manual Retries

To rerun for troubleshooting:
```bash
Summarizer/bin/run_alert.sh
```
Or replay into a scratch directory (limit article count if needed):
```bash
python3 -m Summarizer.cli run --output-dir runs/manual-replay --max-articles 3
```
- For Cloudflare-guarded links, install the url-to-md CLI (`npm install -g url-to-markdown-cli-tool`) so the pipeline can extract Markdown when standard HTTP fails.
- `ALERT_DIGEST_EMAIL` causes the CLI to create `digest.eml`. SMTP delivery only happens when the CLI is run with `--smtp-send` (the Mail rule template does this; `Summarizer/bin/run_alert.sh` does not).

## 7. Future Enhancements

- Optional Slack/email integrations for digest delivery.
