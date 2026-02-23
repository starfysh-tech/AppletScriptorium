#!/usr/bin/env bash
# CommitCraft Issue Validation Script
#
# Validates GitHub issue status before committing.
# Output format: KEY: VALUE (one per line, parseable by command)
#
# STATUS values:
#   OK         - Issue found, all checks passed
#   INCOMPLETE - Issue has unchecked acceptance criteria
#   BLOCKED    - Issue has blocking label
#   NOT_FOUND  - Issue number extracted but doesn't exist
#   NO_ISSUE   - No issue number in branch name
#   ERROR      - Prerequisites not met (gh CLI)

set -euo pipefail

# Prerequisites
if ! command -v gh &>/dev/null; then
    echo "STATUS: ERROR"
    echo "ERROR: gh CLI not installed"
    echo "FIX: brew install gh"
    exit 0
fi

if ! gh auth status &>/dev/null 2>&1; then
    echo "STATUS: ERROR"
    echo "ERROR: gh CLI not authenticated"
    echo "FIX: gh auth login"
    exit 0
fi

# Extract issue from branch name
BRANCH=$(git branch --show-current 2>/dev/null || echo "")
# Try to extract from end first (e.g., feature/description-305), then any number
ISSUE_NUM=$(echo "$BRANCH" | grep -oE '[0-9]+$' | head -1 || echo "")
if [ -z "$ISSUE_NUM" ]; then
    ISSUE_NUM=$(echo "$BRANCH" | grep -oE '[0-9]+' | head -1 || echo "")
fi

if [ -z "$ISSUE_NUM" ]; then
    echo "STATUS: NO_ISSUE"
    echo "BRANCH: $BRANCH"
    echo "INFO: Epic/feature branch - issue tracking per commit"
    exit 0
fi

# Single API call for issue data
ISSUE_JSON=$(gh issue view "$ISSUE_NUM" --json number,title,state,labels,body 2>/dev/null || echo "")

if [ -z "$ISSUE_JSON" ]; then
    echo "STATUS: NOT_FOUND"
    echo "ISSUE: $ISSUE_NUM"
    exit 0
fi

# Parse issue data
TITLE=$(echo "$ISSUE_JSON" | jq -r '.title // "Unknown"')
STATE=$(echo "$ISSUE_JSON" | jq -r '.state // "unknown"')
LABELS=$(echo "$ISSUE_JSON" | jq -r '[.labels[].name] | join(",")' 2>/dev/null || echo "")
BODY=$(echo "$ISSUE_JSON" | jq -r '.body // ""')

# Check for blocking labels
if echo "$LABELS" | grep -qiE "blocked|on-hold|needs-discussion"; then
    echo "STATUS: BLOCKED"
    echo "ISSUE: $ISSUE_NUM"
    echo "TITLE: $TITLE"
    echo "LABELS: $LABELS"
    echo "REASON: Issue has blocking label"
    exit 0
fi

# Check acceptance criteria (count + items for context)
# Note: grep -c outputs 0 on no matches but exits with 1, so we use || true
CHECKED=$(echo "$BODY" | grep -cE '^\s*-\s*\[x\]' || true)
UNCHECKED=$(echo "$BODY" | grep -cE '^\s*-\s*\[\s*\]' || true)
# Handle empty output (shouldn't happen but be safe)
CHECKED=${CHECKED:-0}
UNCHECKED=${UNCHECKED:-0}

if [ "$UNCHECKED" -gt 0 ]; then
    echo "STATUS: INCOMPLETE"
    echo "ISSUE: $ISSUE_NUM"
    echo "TITLE: $TITLE"
    echo "CHECKED: $CHECKED"
    echo "UNCHECKED: $UNCHECKED"
    echo "ITEMS:"
    echo "$BODY" | grep -E '^\s*-\s*\[\s*\]' | head -5 | sed 's/^/  /'
    exit 0
fi

# All checks passed
echo "STATUS: OK"
echo "ISSUE: $ISSUE_NUM"
echo "TITLE: $TITLE"
echo "STATE: $STATE"
exit 0
