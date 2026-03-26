#!/bin/bash

# CommitCraft Release Analyzer
# Analyzes repository for release readiness and version bumping

set -euo pipefail

echo "RELEASE_ANALYZE_START"
echo "=== CommitCraft Release Analysis ==="
echo ""

# Check we're on main branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "✗ Not on main branch"
    echo ""
    echo "Current branch: $CURRENT_BRANCH"
    echo "Releases must be created from the main branch"
    echo ""
    echo "Run: git checkout main"
    exit 1
fi

echo "✓ On main branch"

# Check for gh CLI
if ! command -v gh &> /dev/null; then
    echo "✗ GitHub CLI (gh) not found"
    echo ""
    echo "Install: brew install gh"
    echo "Then authenticate: gh auth login"
    exit 1
fi

# Check gh authentication
if ! gh auth status &> /dev/null; then
    echo "✗ GitHub CLI not authenticated"
    echo ""
    echo "Run: gh auth login"
    exit 1
fi

# Check for clean working tree
if [ -n "$(git status --porcelain)" ]; then
    echo "✗ Working tree has uncommitted changes"
    echo ""
    echo "Commit or stash changes before creating a release"
    exit 1
fi

echo "✓ Working tree is clean"
echo "✓ GitHub CLI authenticated"
echo ""

# Get latest v-prefixed semver tag (ignores bare numeric tags like 1.1.0)
LATEST_TAG=$(git tag --sort=-v:refname | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | head -1)

if [ -z "$LATEST_TAG" ]; then
    echo "⚠  No existing tags found"
    echo ""
    echo "Suggested first version: v1.0.0"
    echo "Commits in repository: $(git rev-list --count HEAD)"
    echo "CURRENT_VERSION: none"
    echo "NEW_VERSION: v1.0.0"
    echo "BUMP_TYPE: initial"
    echo "COMMIT_COUNT: $(git rev-list --count HEAD)"
    echo "RELEASE_ANALYZE_END"
    exit 0
fi

echo "Current version: ${LATEST_TAG}"

# Parse current version (assumes vMAJOR.MINOR.PATCH format)
if [[ ! $LATEST_TAG =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    echo "✗ Tag format not recognized (expected vMAJOR.MINOR.PATCH)"
    echo "Found: $LATEST_TAG"
    exit 1
fi

MAJOR="${BASH_REMATCH[1]}"
MINOR="${BASH_REMATCH[2]}"
PATCH="${BASH_REMATCH[3]}"

# Get commits since last tag (exclude merge commits to avoid double-counting)
COMMITS_SINCE=$(git log "${LATEST_TAG}..HEAD" --oneline --no-merges)
COMMIT_COUNT=$(echo "$COMMITS_SINCE" | grep -c . || echo 0)

if [ "$COMMIT_COUNT" -eq 0 ]; then
    echo "⚠  No commits since ${LATEST_TAG}"
    echo ""
    echo "Nothing to release"
    echo "CURRENT_VERSION: ${LATEST_TAG}"
    echo "NEW_VERSION: ${LATEST_TAG}"
    echo "BUMP_TYPE: none"
    echo "COMMIT_COUNT: 0"
    echo "RELEASE_ANALYZE_END"
    exit 0
fi

echo "Commits since release: ${COMMIT_COUNT}"
echo ""

# Categorize commits
BREAKING_COUNT=0
FEAT_COUNT=0
FIX_COUNT=0
DOCS_COUNT=0
OTHER_COUNT=0

# Check for breaking changes in full commit bodies (single-pass)
BREAKING_COUNT=$(git log "${LATEST_TAG}..HEAD" --no-merges --format=%B | grep -cE "BREAKING CHANGE|^[a-z]+!(\(|:)" || echo 0)

# Count by commit type (single awk pass over oneline output)
read -r FEAT_COUNT FIX_COUNT DOCS_COUNT PERF_COUNT REVERT_COUNT <<< "$(echo "$COMMITS_SINCE" | awk '
  /^[a-f0-9]+ feat(!?\(|!?:)/   {f++}
  /^[a-f0-9]+ fix(!?\(|!?:)/    {x++}
  /^[a-f0-9]+ docs(!?\(|!?:)/   {d++}
  /^[a-f0-9]+ perf(!?\(|!?:)/   {p++}
  /^[a-f0-9]+ revert(!?\(|!?:)/ {r++}
  END {print f+0, x+0, d+0, p+0, r+0}
')"
OTHER_COUNT=$((COMMIT_COUNT - FEAT_COUNT - FIX_COUNT - DOCS_COUNT - PERF_COUNT - REVERT_COUNT))

# Display categorization
echo "Commit breakdown:"
if [ "$BREAKING_COUNT" -gt 0 ]; then
    echo "  Breaking changes: ${BREAKING_COUNT}"
fi
if [ "$FEAT_COUNT" -gt 0 ]; then
    echo "  Features: ${FEAT_COUNT}"
fi
if [ "$FIX_COUNT" -gt 0 ]; then
    echo "  Bug fixes: ${FIX_COUNT}"
fi
if [ "$DOCS_COUNT" -gt 0 ]; then
    echo "  Documentation: ${DOCS_COUNT}"
fi
if [ "$PERF_COUNT" -gt 0 ]; then
    echo "  Performance: ${PERF_COUNT}"
fi
if [ "$REVERT_COUNT" -gt 0 ]; then
    echo "  Reverts: ${REVERT_COUNT}"
fi
if [ "$OTHER_COUNT" -gt 0 ]; then
    echo "  Other: ${OTHER_COUNT}"
fi
echo ""

# Calculate version bump
if [ "$BREAKING_COUNT" -gt 0 ]; then
    BUMP_TYPE="major"
    NEW_MAJOR=$((MAJOR + 1))
    NEW_MINOR=0
    NEW_PATCH=0
elif [ "$FEAT_COUNT" -gt 0 ]; then
    BUMP_TYPE="minor"
    NEW_MAJOR=$MAJOR
    NEW_MINOR=$((MINOR + 1))
    NEW_PATCH=0
else
    BUMP_TYPE="patch"
    NEW_MAJOR=$MAJOR
    NEW_MINOR=$MINOR
    NEW_PATCH=$((PATCH + 1))
fi

NEW_VERSION="v${NEW_MAJOR}.${NEW_MINOR}.${NEW_PATCH}"

echo "Suggested bump: ${BUMP_TYPE}"
echo "New version: ${NEW_VERSION}"
echo ""

# Show recent commits for context
echo "Recent commits:"
echo "$COMMITS_SINCE" | head -10
if [ "$COMMIT_COUNT" -gt 10 ]; then
    echo "... and $((COMMIT_COUNT - 10)) more"
fi
echo ""

echo "✓ Ready to create release"
echo ""

# Parseable output
echo "CURRENT_VERSION: ${LATEST_TAG}"
echo "NEW_VERSION: ${NEW_VERSION}"
echo "BUMP_TYPE: ${BUMP_TYPE}"
echo "COMMIT_COUNT: ${COMMIT_COUNT}"

# Structured commit output (unit separator \x1f delimited)
echo ""
echo "COMMITS_START"
git log "${LATEST_TAG}..HEAD" --format="%h$(printf '\x1f')%s" --no-merges
echo "COMMITS_END"

echo "RELEASE_ANALYZE_END"
