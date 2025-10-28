#!/usr/bin/env bash
# CommitCraft Pre-Commit Analysis Script
#
# Gathers comprehensive context before creating a commit
# Used by /commitcraft-push command and other commit workflows
#
# Output: Structured report with sync status, diffs, security checks, etc.
# Can be called directly or output redirected to a file

set -euo pipefail

# Detect repository directory
# Priority: 1) First parameter if it's a directory, 2) Env var, 3) Current directory
REPO_DIR=""
if [ -n "${1:-}" ] && [ -d "$1" ]; then
    REPO_DIR="$1"
    shift
elif [ -n "${CLAUDE_CODE_WORKING_DIR:-}" ]; then
    REPO_DIR="$CLAUDE_CODE_WORKING_DIR"
else
    REPO_DIR="$PWD"
fi

# Validate we're in a git repo
if ! git -C "$REPO_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    echo "Error: Not a git repository: $REPO_DIR" >&2
    exit 1
fi

# Helper function for git commands
git_cmd() {
    git -C "$REPO_DIR" "$@"
}

# Configuration
OUTPUT_FILE="${1:-/dev/stdout}"

# Header
{
    echo "================================================================================"
    echo "GIT PRE-COMMIT ANALYSIS"
    echo "================================================================================"
    echo ""
    echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Repository: $(git_cmd rev-parse --show-toplevel 2>/dev/null || echo 'Unknown')"
    echo ""

    # ============================================================================
    # BRANCH & SYNC STATUS
    # ============================================================================
    echo "## Branch & Sync Status"
    echo "--------------------------------------------------------------------------------"

    CURRENT_BRANCH=$(git_cmd rev-parse --abbrev-ref HEAD 2>/dev/null || echo "detached")
    echo "Current branch: $CURRENT_BRANCH"

    if [ "$CURRENT_BRANCH" = "HEAD" ]; then
        echo "⚠️  WARNING: Detached HEAD state"
    fi

    # Fetch remote silently
    echo "Fetching from remote..."
    git_cmd fetch origin --quiet 2>/dev/null || echo "⚠️  Could not fetch from remote"

    # Check sync status
    echo ""
    git_cmd status -sb

    # Count commits ahead/behind
    AHEAD_BEHIND=$(git_cmd rev-list --left-right --count HEAD...@{upstream} 2>/dev/null || echo "0	0")
    AHEAD=$(echo "$AHEAD_BEHIND" | cut -f1)
    BEHIND=$(echo "$AHEAD_BEHIND" | cut -f2)

    echo ""
    if [ "$BEHIND" -gt 0 ]; then
        echo "⚠️  Your branch is $BEHIND commits BEHIND remote - consider pulling first"
    fi
    if [ "$AHEAD" -gt 0 ]; then
        echo "ℹ️  Your branch is $AHEAD commits AHEAD of remote"
    fi
    echo ""

    # ============================================================================
    # WORKING TREE STATUS
    # ============================================================================
    echo "## Working Tree Status"
    echo "--------------------------------------------------------------------------------"

    PORCELAIN=$(git_cmd status --porcelain 2>/dev/null)

    if [ -z "$PORCELAIN" ]; then
        echo "✓ No changes (working tree clean)"
    else
        echo "Changes detected:"
        echo ""
        git_cmd status --porcelain
    fi
    echo ""

    # ============================================================================
    # CHANGED FILES SUMMARY
    # ============================================================================
    echo "## Changed Files Summary"
    echo "--------------------------------------------------------------------------------"

    STAGED=$(git_cmd diff --cached --stat 2>/dev/null)
    UNSTAGED=$(git_cmd diff --stat 2>/dev/null)

    if [ -n "$STAGED" ]; then
        echo "Staged changes:"
        git_cmd diff --cached --stat
    else
        echo "No staged changes"
    fi

    echo ""

    if [ -n "$UNSTAGED" ]; then
        echo "Unstaged changes:"
        git_cmd diff --stat
    else
        echo "No unstaged changes"
    fi
    echo ""

    # ============================================================================
    # UNTRACKED FILES
    # ============================================================================
    echo "## Untracked Files"
    echo "--------------------------------------------------------------------------------"

    UNTRACKED=$(git_cmd ls-files --others --exclude-standard 2>/dev/null)

    if [ -z "$UNTRACKED" ]; then
        echo "No untracked files"
    else
        echo "$UNTRACKED"
    fi
    echo ""

    # ============================================================================
    # SECURITY SCAN
    # ============================================================================
    echo "## Security Scan"
    echo "--------------------------------------------------------------------------------"

    # Check for common secrets in staged changes
    SECRETS=$(git_cmd diff --cached 2>/dev/null | grep -iE "password|secret|api_key|token|credential|private_key" || true)

    if [ -z "$SECRETS" ]; then
        echo "✓ No obvious secrets detected"
    else
        echo "⚠️  POTENTIAL SECRETS DETECTED:"
        echo "$SECRETS"
    fi
    echo ""

    # ============================================================================
    # LARGE FILES CHECK
    # ============================================================================
    echo "## Large Files Check"
    echo "--------------------------------------------------------------------------------"

    # Files with changes >1000 lines
    LARGE_FILES=$(git_cmd diff --cached --stat 2>/dev/null | grep -E '\|\s+[0-9]{4,}\s' || true)

    if [ -z "$LARGE_FILES" ]; then
        echo "✓ No unusually large files"
    else
        echo "⚠️  Large file changes detected:"
        echo "$LARGE_FILES"
    fi
    echo ""

    # ============================================================================
    # CODE QUALITY MARKERS
    # ============================================================================
    echo "## Code Quality Markers"
    echo "--------------------------------------------------------------------------------"

    # Check for TODOs/FIXMEs in staged changes
    TODOS=$(git_cmd diff --cached 2>/dev/null | grep -iE "TODO|FIXME|XXX|HACK" || true)

    if [ -z "$TODOS" ]; then
        echo "✓ No TODO/FIXME markers in staged changes"
    else
        echo "ℹ️  TODO/FIXME markers found:"
        echo "$TODOS"
    fi
    echo ""

    # ============================================================================
    # RECENT COMMITS (for context)
    # ============================================================================
    echo "## Recent Commit History"
    echo "--------------------------------------------------------------------------------"

    git_cmd log --oneline -5 2>/dev/null || echo "No commit history"
    echo ""

    # ============================================================================
    # RECOMMENDED ACTIONS
    # ============================================================================
    echo "## Recommended Actions"
    echo "--------------------------------------------------------------------------------"

    if [ "$BEHIND" -gt 0 ]; then
        echo "⚠️  Pull remote changes: git pull --rebase origin $CURRENT_BRANCH"
    fi

    if [ -n "$UNSTAGED" ]; then
        echo "ℹ️  Stage changes: git add <files>"
    fi

    if [ -n "$UNTRACKED" ]; then
        echo "ℹ️  Review untracked files: add to .gitignore or git add"
    fi

    if [ -n "$SECRETS" ]; then
        echo "⚠️  REVIEW POTENTIAL SECRETS before committing"
    fi

    echo ""
    echo "================================================================================"
    echo "END OF ANALYSIS"
    echo "================================================================================"

} > "$OUTPUT_FILE"

exit 0
