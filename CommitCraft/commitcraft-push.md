---
description: "CommitCraft enhanced git commit workflow"
allowed-tools: ["Bash", "Read", "Edit"]
---

# CommitCraft Enhanced Git Commit Workflow

Creates commits with security scanning, conventional format, and Claude attribution.

## Workflow

### Step 0: Check for Required Tools

Check if `.claude/scripts/commitcraft-analyze.sh` exists in this repository.

**If NOT found, stop and show this message:**

```
❌ CommitCraft tools not installed in this repository.

The /commitcraft-push command requires commitcraft-analyze.sh for:
- Security scanning (secret detection)
- Large file detection
- Branch sync status (ahead/behind remote)
- Enhanced commit context

To install tools in this repo:
```bash
commitcraft-init
```

After installation, run /commitcraft-push again.
```

**IMPORTANT: Show this error message and STOP. Do NOT attempt to run installation commands. Wait for the user to install manually.**

**Do NOT proceed without the script. Stop here.**

---

**If found, continue to Step 1.**

---

### Step 1: Gather Complete Context

Execute the analysis script once to capture all commit context:

```bash
.claude/scripts/commitcraft-analyze.sh
```

This single execution provides:
- Branch sync status (ahead/behind remote)
- Security scan (potential secrets)
- Large file detection (>1000 lines changed)
- Code quality markers (TODO/FIXME)
- Recent commit history
- Staged/unstaged changes

Review the output before proceeding to Step 2.

---

### Step 2: Review Changes

For each changed file, review key changes:
```bash
git diff <file>
```

**Critical checks:**
- Flag any secrets/credentials
- Warn about large files
- Note any TODOs or commented-out code

---

### Step 3: Generate Commit Message

Follow Conventional Commits format:

```
<type>(<scope>): <subject>
[BLANK LINE]
<body>
[BLANK LINE]
<footer>
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

**Format rules:**
- **Scope** (optional): Noun describing affected area
- **Subject**: Imperative mood ("Add feature" not "Added feature"), ≤50 chars
- **Body**: Detailed description, ≤72 chars/line
- **Footer**: "BREAKING CHANGE: <description>" or issue references

---

### Step 4: Stage and Commit

Stage relevant files:
```bash
git add <files>
```

Create commit with attribution:
```bash
git commit -m "$(cat <<'EOF'
<user-approved message>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

### Step 5: Push (If Requested)

```bash
git push origin <branch-name>
```

---

## Important Reminders

- Reference `.claude/CLAUDE.md` or `CLAUDE.md` for project-specific commit rules
- STOP if secrets detected - review before committing
- Verify commit message is accurate and concise
- Goal: Useful commit history for future developers
