#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${REPO_ROOT}/Summarizer:${PYTHONPATH:-}"

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
OUTPUT_DIR="${PRO_ALERT_OUTPUT_DIR:-${REPO_ROOT}/runs/${TIMESTAMP}}"
mkdir -p "$OUTPUT_DIR"
LOG_FILE="$OUTPUT_DIR/workflow.log"

ARGS=(--output-dir "$OUTPUT_DIR")
[[ -n "${PRO_ALERT_STUB_MANIFEST:-}" ]] && ARGS+=(--stub-manifest "$PRO_ALERT_STUB_MANIFEST")
[[ -n "${PRO_ALERT_MODEL:-}" ]] && ARGS+=(--model "$PRO_ALERT_MODEL")
[[ -n "${PRO_ALERT_MAX_ARTICLES:-}" ]] && ARGS+=(--max-articles "$PRO_ALERT_MAX_ARTICLES")

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting run with args: ${ARGS[*]}"
  python3 -m Summarizer.cli run "${ARGS[@]}"
} >> "$LOG_FILE" 2>&1
STATUS=$?

notify() {
  local message="$1"
  osascript -e "display notification \"${message}\" with title \"PRO Alert Summarizer\"" >/dev/null 2>&1 || true
  if [[ -n "${PRO_ALERT_EMAIL_RECIPIENT:-}" ]] && command -v mail >/dev/null 2>&1; then
    mail -s "PRO Alert Summarizer" "$PRO_ALERT_EMAIL_RECIPIENT" < "$LOG_FILE" || true
  fi
}

if [[ $STATUS -ne 0 ]]; then
  notify "Run failed (exit $STATUS). See log."
else
  if [[ "${PRO_ALERT_NOTIFY_ON_SUCCESS:-0}" == "1" ]]; then
    notify "Run completed successfully. Output in $OUTPUT_DIR"
  fi
fi

exit $STATUS
