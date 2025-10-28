---
description: "CommitCraft automated release workflow with semver"
allowed-tools: ["Bash", "Read"]
---

# CommitCraft Automated Release Workflow

Fully automated semantic versioning and GitHub release creation.

**This command runs automatically unless there's a problem. Only stops for blockers.**

## Workflow

### Step 1: Run Analysis and Check for Blockers

Execute analysis script (use working directory from <env> context):
```bash
~/.claude/scripts/commitcraft-release-analyze.sh <working-directory>
```

**Immediately check output for BLOCKERS:**

1. **No gh CLI** → STOP and show:
   ```
   🛑 BLOCKED: GitHub CLI not found

   Install: brew install gh
   Then authenticate: gh auth login
   ```

2. **Not authenticated** → STOP and show:
   ```
   🛑 BLOCKED: GitHub CLI not authenticated

   Run: gh auth login
   ```

3. **Uncommitted changes** → STOP and show:
   ```
   🛑 BLOCKED: Working tree has uncommitted changes

   Commit or stash changes before creating a release.
   Run: git status
   ```

4. **No commits since last tag** → STOP and show:
   ```
   🛑 BLOCKED: No commits since last release

   Nothing to release.
   ```

5. **No existing tags** → Note and continue:
   ```
   ⚠️  No existing tags found

   This will be the first release (v1.0.0).
   ```

**If NO blockers → Continue to Step 2 automatically.**

---

### Step 2: Extract Version Information

Parse the output from analysis script to extract:
- Current version (e.g., `v3.1.0`)
- New version (e.g., `v3.2.0`)
- Bump type (major/minor/patch)
- Commit counts by category

---

### Step 3: Generate Release Notes

Get commits since last tag and categorize by conventional commit type:

```bash
# Get all commits with full messages
git log <LAST_TAG>..HEAD --format="%H|%s|%b"
```

**Build release notes with sections:**

```markdown
## 🚨 Breaking Changes

<List commits with BREAKING CHANGE in body>

## ✨ Features

<List feat: commits>

## 🐛 Bug Fixes

<List fix: commits>

## 📚 Documentation

<List docs: commits>

## 🔧 Other Changes

<List remaining commits>
```

**Format per commit:**
- Extract subject line (remove emoji and type prefix if present)
- Include scope if available: `feat(api): add endpoint` → `**API:** Add endpoint`
- For breaking changes, extract BREAKING CHANGE description from body

---

### Step 4: Create Git Tag

Create annotated tag with new version:
```bash
git tag -a <NEW_VERSION> -m "<NEW_VERSION>"
```

**Example:**
```bash
git tag -a v3.2.0 -m "v3.2.0"
```

---

### Step 5: Push Tag

Push the new tag to origin:
```bash
git push origin <NEW_VERSION>
```

---

### Step 6: Create GitHub Release

Create release using GitHub CLI:
```bash
gh release create <NEW_VERSION> \
  --title "<NEW_VERSION> - <BRIEF_SUMMARY>" \
  --notes "$(cat <<'EOF'
<GENERATED_RELEASE_NOTES>
EOF
)"
```

**Title format:**
- Extract 1-3 main topics from feature/fix commits
- Example: `v3.2.0 - Release Automation & Bug Fixes`

---

### Step 7: Report Success

Show final status:
```
✓ Created tag: <NEW_VERSION>
✓ Pushed to: origin
✓ Published release: <RELEASE_URL>

Release notes:
<SUMMARY>
```

---

## Blocker Summary

**Only stop for these issues:**
- 🛑 GitHub CLI missing or not authenticated
- 🛑 Uncommitted changes in working tree
- 🛑 No commits since last release
- 🛑 Tools not installed

**Everything else runs automatically without user interaction.**

---

## Version Bump Rules

**Automatic detection based on conventional commits:**

| Condition | Bump Type | Example |
|-----------|-----------|---------|
| Any commit contains `BREAKING CHANGE` in body | **Major** | v2.0.0 → v3.0.0 |
| Has `feat:` commits (no breaking changes) | **Minor** | v2.0.0 → v2.1.0 |
| Has `fix:` commits (no features or breaking) | **Patch** | v2.0.0 → v2.0.1 |
| Other commits only | **Patch** | v2.0.0 → v2.0.1 |

**For first release (no tags):**
- Default to `v1.0.0`

---

## Release Notes Format

**Section priority (only include non-empty sections):**

1. 🚨 **Breaking Changes** - Changes that break backward compatibility
2. ✨ **Features** - New features and enhancements
3. 🐛 **Bug Fixes** - Bug fixes and corrections
4. 📚 **Documentation** - Documentation updates
5. 🔧 **Other Changes** - Refactoring, tests, chores, etc.

**Commit format:**
- Use subject line as bullet point
- Strip type prefix and emoji from subject
- Preserve scope as bold prefix: `feat(api): add endpoint` → `**API:** Add endpoint`
- For breaking changes, include description from commit body
