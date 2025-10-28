---
description: "CommitCraft automated git commit and push workflow"
allowed-tools: ["Bash", "Read", "Edit"]
---

# CommitCraft Automated Git Workflow

Fully automated commit workflow with security scanning, conventional format, and Claude attribution.

**This command runs automatically unless there's a problem. Only stops for blockers.**

## Workflow

### Step 1: Run Analysis and Check for Blockers

Execute analysis script (use working directory from <env> context):
```bash
~/.claude/scripts/commitcraft-analyze.sh <working-directory>
```

**Immediately check output for BLOCKERS:**

1. **Secrets detected** → STOP and show:
   ```
   🛑 BLOCKED: Potential secrets detected in changes

   Found: [list secret patterns]

   Review changes and remove secrets before committing.
   Run 'git diff' to inspect changes.
   ```

2. **Behind remote** → STOP and show:
   ```
   🛑 BLOCKED: Branch is behind origin/main

   Run: git pull --rebase origin main

   Then run /commitcraft-push again.
   ```

3. **Merge conflicts** → STOP and show:
   ```
   🛑 BLOCKED: Merge conflicts detected

   Resolve conflicts manually, then run /commitcraft-push again.
   ```

4. **Large files (>1000 lines changed)** → Note but continue:
   ```
   ⚠️  WARNING: Large files detected (will still commit)
   [list files]
   ```

**If NO blockers → Continue to Step 2 automatically.**

---

### Step 2: Stage All Changes

Stage all modified and untracked files automatically:
```bash
git add -A
```

---

### Step 3: Generate Commit Message

Analyze changes and generate Conventional Commits format message automatically.

**Format:**
```
<type>(<scope>): <subject>

<body>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Types:**
- `✨ feat` - New feature
- `🐛 fix` - Bug fix
- `📚 docs` - Documentation changes
- `💎 style` - Code style/formatting
- `♻️ refactor` - Code restructuring
- `🧪 test` - Test-related changes
- `🏗️ chore` - Build process/auxiliary tools
- `⚡ perf` - Performance improvements
- `🌱 ci` - CI/CD pipeline changes

**Rules:**
- **Scope** (optional): Component/area affected
- **Subject**: Imperative mood, ≤50 chars
- **Body**: Detailed description, ≤72 chars/line
- Reference `.claude/CLAUDE.md` or `CLAUDE.md` for project-specific rules

---

### Step 4: Update CHANGELOG (if exists)

Check if CHANGELOG.md exists:
```bash
[ -f CHANGELOG.md ] && echo "exists" || echo "skip"
```

**If CHANGELOG.md exists:**

1. Parse commit message from Step 3 to extract:
   - **Type**: Extract from emoji prefix (✨/🐛/📚/etc.)
   - **Scope**: Text between `(` and `)` if present
   - **Subject**: Text after `:` (trim whitespace)

2. Map type to CHANGELOG category:
   - ✨ `feat` → `### Added`
   - 🐛 `fix` → `### Fixed`
   - 📚 `docs`, ♻️ `refactor`, ⚡ `perf`, 💎 `style`, 🏗️ `chore`, 🧪 `test`, 🌱 `ci` → `### Changed`

3. Format entry:
   - With scope: `- **<scope>:** <subject>`
   - No scope: `- <subject>`

4. Use Edit tool to insert entry under `[Unreleased]` section in correct category
   - Find the category header (e.g., `### Added`)
   - Insert new entry as first item under that header

5. Stage CHANGELOG.md:
   ```bash
   git add CHANGELOG.md
   ```

**If CHANGELOG.md doesn't exist:** Skip this step entirely.

---

### Step 5: Commit

Create commit automatically:
```bash
git commit -m "$(cat <<'EOF'
<generated message>
EOF
)"
```

---

### Step 6: Push

Push to origin automatically:
```bash
git push origin <branch-name>
```

---

### Step 7: Report Success

Show final status:
```
✓ Committed: <commit-hash>
✓ Pushed to: origin/<branch-name>

<commit message>
```

---

## Blocker Summary

**Only stop for these issues:**
- 🛑 Secrets detected
- 🛑 Behind remote (needs rebase)
- 🛑 Merge conflicts
- 🛑 Tools not installed

**Everything else runs automatically without user interaction.**
