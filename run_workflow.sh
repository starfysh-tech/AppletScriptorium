#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${ROOT}/Summarizer:${PYTHONPATH:-}"
RUN_ID="$(date +%Y%m%d-%H%M%S)"
export PYTHONPATH="$ROOT/Summarizer:${PYTHONPATH:-}"
RUN_DIR="$ROOT/runs/$RUN_ID"
LOG_FILE="$RUN_DIR/workflow.log"

mkdir -p "$RUN_DIR/articles" "$RUN_DIR/summaries"
exec > >(tee "$LOG_FILE") 2>&1

log() {
    printf '[%s] %s\n' "$(date +"%Y-%m-%d %H:%M:%S")" "$*"
}

need_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        log "ERROR: Required command '$1' not found."
        exit 1
    fi
}

log "Run directory: $RUN_DIR"
need_cmd python3
need_cmd ollama
need_cmd osascript

log "Checking Python dependencies..."
python3 - <<'PY' || { log "Install missing deps: python3 -m pip install -r Summarizer/requirements.txt"; exit 1; }
try:
    import httpx  # type: ignore
    import readability  # type: ignore
except Exception as exc:
    raise SystemExit(f"Missing dependency: {exc}")
PY

log "Ensuring Ollama model 'granite4:tiny-h' is available..."
if ! ollama list | grep -q 'granite4:tiny-h'; then
    log "Pulling model granite4:tiny-h ..."
    ollama pull granite4:tiny-h >/dev/null
fi

ALERT_EML="$RUN_DIR/alert.eml"
log "Capturing latest Google Alert email to $ALERT_EML"
osascript "$ROOT/Summarizer/fetch-alert-source.applescript" "$ALERT_EML"

ALERT_TSV="$RUN_DIR/alert.tsv"
log "Extracting link metadata -> $ALERT_TSV"
python3 "$ROOT/Summarizer/clean-alert.py" "$ALERT_EML" > "$ALERT_TSV"

log "Fetching articles, cleaning content, and generating summaries..."
python3 - <<PY
import csv
import json
import re
from pathlib import Path

from article_fetcher import FetchConfig, FetchError, fetch_article
from content_cleaner import extract_content
from summarizer import SummarizerConfig, SummarizerError, summarize_article

root = Path("$ROOT")
run_dir = Path("$RUN_DIR")
articles_dir = run_dir / "articles"
summaries_dir = run_dir / "summaries"
articles_dir.mkdir(exist_ok=True)
summaries_dir.mkdir(exist_ok=True)

alert_rows = []
with open("$ALERT_TSV", newline="", encoding="utf-8") as csvfile:
    reader = csv.reader(csvfile, delimiter="\t")
    for row in reader:
        if len(row) < 2:
            continue
        title, url, *rest = row
        publisher = rest[0] if rest else ""
        snippet = rest[1] if len(rest) > 1 else ""
        alert_rows.append({"title": title, "url": url, "publisher": publisher, "snippet": snippet})

def slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "article"

fetch_cfg = FetchConfig(allow_cache=False)
sum_cfg = SummarizerConfig(model="granite4:tiny-h")

results = []
for idx, meta in enumerate(alert_rows, start=1):
    title = meta["title"]
    url = meta["url"]
    slug_name = f"{idx:02d}-{slug(title)[:40]}"
    html_path = articles_dir / f"{slug_name}.html"

    try:
        print(f"[fetch] {url}")
        html = fetch_article(url, fetch_cfg)
        html_path.write_text(html, encoding="utf-8")
    except FetchError as exc:
        print(f"[fetch][ERROR] {url} -> {exc}")
        continue

    try:
        content_text = extract_content(html)
        if not content_text.strip():
            raise ValueError("no content extracted")
        content_path = articles_dir / f"{slug_name}.content.md"
        content_path.write_text(content_text, encoding="utf-8")
    except Exception as exc:
        print(f"[clean][ERROR] {url} -> {exc}")
        continue

    article_payload = {
        "title": title,
        "url": url,
        "publisher": meta["publisher"],
        "snippet": meta["snippet"],
        "content": content_text,
    }

    try:
        summary = summarize_article(article_payload, config=sum_cfg)
        summary_path = summaries_dir / f"{slug_name}.summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        results.append(summary)
        print(f"[summarize] {title}")
    except SummarizerError as exc:
        print(f"[summarize][ERROR] {url} -> {exc}")

(summaries_dir / "summaries.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"[done] processed {len(results)} articles; artifacts under {run_dir}")
PY

log "Workflow complete. Outputs:"
log " - Raw alert:     $ALERT_EML"
log " - Link metadata: $ALERT_TSV"
log " - Articles dir:  $RUN_DIR/articles"
log " - Summaries dir: $RUN_DIR/summaries"
log " - Log file:      $LOG_FILE"
