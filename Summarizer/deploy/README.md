# Deployment Guide — PRO Alert Summarizer

This repository ships the tooling and scripts needed to capture the latest PRO alert, fetch the linked articles, summarize them with Ollama, and emit HTML/text digests. To run the pipeline on a schedule from your Mac, follow these steps.

## 1. Prerequisites

- **Python 3.11+**
- **Apple Mail** with script support enabled (for AppleScript to fetch the alert)
- **Ollama** installed and running (`brew install ollama` and `ollama serve`)
- Pull the summarizer model:
  ```bash
  ollama pull granite4:tiny-h
  ```

Install Python dependencies once:
```bash
python3 -m pip install -r Summarizer/requirements.txt
```

## 2. Test the Pipeline Manually

From the repo root, generate a full run to ensure everything works:
```bash
python3 -m Summarizer.cli run --output-dir runs/manual-test
```
This creates:
- `runs/manual-test/alert.eml` (raw email)
- `.../alert.tsv` (link metadata)
- `.../articles/` (fetched HTML, cleaned content, summaries)
- `.../digest.html` / `digest.txt`
- `.../workflow.log`

## 3. Wrapper Script

`Summarizer/bin/run_pro_alert.sh` wraps the CLI for cron/automation. It:
- Sets `PYTHONPATH`
- Chooses an output dir (default `runs/<timestamp>`, overridable via `PRO_ALERT_OUTPUT_DIR`)
- Executes the CLI
- Sends macOS notifications (and optional email using `mail`)

Optional environment variables (set in `~/.pro-alert-env`):
- `PRO_ALERT_EMAIL_RECIPIENT` — notify on failures.
- `PRO_ALERT_NOTIFY_ON_SUCCESS=1` — also notify when runs succeed.
- `PRO_ALERT_OUTPUT_DIR` — override the default output directory.
- `PRO_ALERT_MODEL`, `PRO_ALERT_STUB_MANIFEST`, `PRO_ALERT_MAX_ARTICLES` — tune behavior.
- `PRO_ALERT_DIGEST_EMAIL` — comma-separated recipients for the generated digest.
- `PRO_ALERT_EMAIL_SENDER` — address used to select the Mail.app account for digest delivery.

## 4. Cron Setup

1. Create `~/.pro-alert-env` and export any of the variables above.
2. Add the cron entry:
   ```cron
   0 7 * * 1-5 /bin/bash -lc 'source ~/.pro-alert-env; /Users/<you>/Code/AppletScriptorium/Summarizer/bin/run_pro_alert.sh'
   ```
3. Confirm with `crontab -l`.

## 5. Logs & Monitoring

- Each run writes to `runs/<timestamp>/workflow.log`.
- Notifications include basic status; full detail is in the log.
- Failures typically imprint the last HTTP status or summarizer error.

## 6. Manual Retries

To rerun for troubleshooting:
```bash
Summarizer/bin/run_pro_alert.sh
```
Or replay into a scratch directory (limit article count if needed):
```bash
python3 -m Summarizer.cli run --output-dir runs/manual-replay --max-articles 3
```
- For Cloudflare-guarded links, install Playwright (`python3 -m pip install playwright` then `playwright install`) so the automation can render the challenge pages headlessly.
- To email the digest automatically, export `PRO_ALERT_DIGEST_EMAIL` (comma-separated) and optionally `PRO_ALERT_EMAIL_SENDER` before running the CLI or wrapper; the plaintext digest is handed to Mail.app via AppleScript.

## 7. Future Enhancements

- Optional Slack/email integrations for digest delivery.
