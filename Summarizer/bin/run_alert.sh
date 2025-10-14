#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${REPO_ROOT}/Summarizer:${PYTHONPATH:-}"

# Backward compatibility: support old PRO_ALERT_* variables
# New variables (ALERT_*) take precedence if both are set
OUTPUT_DIR_VAR="${ALERT_OUTPUT_DIR:-${PRO_ALERT_OUTPUT_DIR:-}}"
MODEL_VAR="${ALERT_MODEL:-${PRO_ALERT_MODEL:-}}"
MAX_ARTICLES_VAR="${ALERT_MAX_ARTICLES:-${PRO_ALERT_MAX_ARTICLES:-}}"
DIGEST_EMAIL_VAR="${ALERT_DIGEST_EMAIL:-${PRO_ALERT_DIGEST_EMAIL:-}}"
EMAIL_RECIPIENT_VAR="${ALERT_EMAIL_RECIPIENT:-${PRO_ALERT_EMAIL_RECIPIENT:-}}"
NOTIFY_ON_SUCCESS_VAR="${ALERT_NOTIFY_ON_SUCCESS:-${PRO_ALERT_NOTIFY_ON_SUCCESS:-0}}"

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
OUTPUT_DIR="${OUTPUT_DIR_VAR:-${REPO_ROOT}/runs/${TIMESTAMP}}"
mkdir -p "$OUTPUT_DIR"
LOG_FILE="$OUTPUT_DIR/workflow.log"

ARGS=(--output-dir "$OUTPUT_DIR")
[[ -n "${MODEL_VAR}" ]] && ARGS+=(--model "$MODEL_VAR")
[[ -n "${MAX_ARTICLES_VAR}" ]] && ARGS+=(--max-articles "$MAX_ARTICLES_VAR")
if [[ -n "${DIGEST_EMAIL_VAR}" ]]; then
  IFS=',' read -r -a __digest_recipients <<< "${DIGEST_EMAIL_VAR}"
  for recipient in "${__digest_recipients[@]}"; do
    trimmed="$(echo "$recipient" | xargs)"
    [[ -n "$trimmed" ]] && ARGS+=(--email-digest "$trimmed")
  done
  unset __digest_recipients
fi

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting run with args: ${ARGS[*]}"
  python3 -m Summarizer.cli run "${ARGS[@]}"
} >> "$LOG_FILE" 2>&1
STATUS=$?

notify() {
  local message="$1"
  osascript -e "display notification \"${message}\" with title \"Google Alert Intelligence\"" >/dev/null 2>&1 || true
  if [[ -n "${EMAIL_RECIPIENT_VAR}" ]] && command -v mail >/dev/null 2>&1; then
    mail -s "Google Alert Intelligence" "$EMAIL_RECIPIENT_VAR" < "$LOG_FILE" || true
  fi
}

if [[ $STATUS -ne 0 ]]; then
  notify "Run failed (exit $STATUS). See log."
else
  if [[ "${NOTIFY_ON_SUCCESS_VAR}" == "1" ]]; then
    notify "Run completed successfully. Output in $OUTPUT_DIR"
  fi
fi

exit $STATUS
