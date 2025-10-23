#!/usr/bin/env bash
# CommitCraft Pre-Commit Analysis Script
#
# Gathers comprehensive context before creating a commit
# Used by /commitcraft-push command and other commit workflows
#
# Output: Structured report with sync status, diffs, security checks, etc.
# Can be called directly or output redirected to a file

set -euo pipefail

# Configuration
OUTPUT_FILE="${1:-/dev/stdout}"

# Header
{
    echo "================================================================================"
    echo "GIT PRE-COMMIT ANALYSIS"
    echo "================================================================================"
    echo ""
    echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Repository: $(git rev-parse --show-toplevel 2>/dev/null || echo 'Unknown')"
    echo ""

    # ============================================================================
    # BRANCH & SYNC STATUS
    # ============================================================================
    echo "## Branch & Sync Status"
    echo "--------------------------------------------------------------------------------"

    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "detached")
    echo "Current branch: $CURRENT_BRANCH"

    if [ "$CURRENT_BRANCH" = "HEAD" ]; then
        echo "⚠️  WARNING: Detached HEAD state"
    fi

    # Fetch remote silently
    echo "Fetching from remote..."
    git fetch origin --quiet 2>/dev/null || echo "⚠️  Could not fetch from remote"

    # Check sync status
    echo ""
    git status -sb

    # Count commits ahead/behind
    AHEAD_BEHIND=$(git rev-list --left-right --count HEAD...@{upstream} 2>/dev/null || echo "0	0")
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

    PORCELAIN=$(git status --porcelain 2>/dev/null)

    if [ -z "$PORCELAIN" ]; then
        echo "✓ No changes (working tree clean)"
    else
        echo "Changes detected:"
        echo ""
        git status --porcelain
    fi
    echo ""

    # ============================================================================
    # CHANGED FILES SUMMARY
    # ============================================================================
    echo "## Changed Files Summary"
    echo "--------------------------------------------------------------------------------"

    STAGED=$(git diff --cached --stat 2>/dev/null)
    UNSTAGED=$(git diff --stat 2>/dev/null)

    if [ -n "$STAGED" ]; then
        echo "Staged changes:"
        git diff --cached --stat
    else
        echo "No staged changes"
    fi

    echo ""

    if [ -n "$UNSTAGED" ]; then
        echo "Unstaged changes:"
        git diff --stat
    else
        echo "No unstaged changes"
    fi
    echo ""

    # ============================================================================
    # UNTRACKED FILES
    # ============================================================================
    echo "## Untracked Files"
    echo "--------------------------------------------------------------------------------"

    UNTRACKED=$(git ls-files --others --exclude-standard 2>/dev/null)

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
    SECRETS=$(git diff --cached 2>/dev/null | grep -iE "password|secret|api_key|token|credential|private_key" || true)

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
    LARGE_FILES=$(git diff --cached --stat 2>/dev/null | grep -E '\|\s+[0-9]{4,}\s' || true)

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
    TODOS=$(git diff --cached 2>/dev/null | grep -iE "TODO|FIXME|XXX|HACK" || true)

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

    git log --oneline -5 2>/dev/null || echo "No commit history"
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
