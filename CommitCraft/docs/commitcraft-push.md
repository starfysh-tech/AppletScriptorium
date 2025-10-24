# CommitCraft Enhanced Git Commit Tool (/commitcraft-push)

## Overview

The `/commitcraft-push` command provides AI-assisted git commits with automated security scanning, conventional commit formatting, and comprehensive change analysis. It combines Claude Code's intelligence with shell-based tooling to create high-quality commit messages while catching potential issues before they reach your repository.

## What It Provides

- **Security scanning** - Detects potential secrets, credentials, API keys
- **Large file detection** - Warns about files with >1000 lines changed
- **Branch sync checking** - Alerts if local is behind remote
- **Code quality markers** - Surfaces TODO/FIXME comments in changes
- **Conventional commits** - Enforces standardized format with emoji prefixes
- **CHANGELOG maintenance** - Auto-updates [Unreleased] section (if CHANGELOG.md exists)
- **Claude attribution** - Automatically adds co-authorship footer
- **Context-aware messages** - Uses full analysis to generate accurate descriptions

## Command Usage

### Basic Workflow

When you run `/commitcraft-push` in Claude Code, the following happens automatically:

1. **Analysis** - Runs `~/.claude/scripts/commitcraft-analyze.sh` for security/sync checking
2. **Blocker check** - Stops if secrets, merge conflicts, or behind remote detected
3. **Stage all** - Runs `git add -A` to stage changes
4. **Generate message** - Creates conventional commit message with Claude
5. **Commit** - Commits with Claude attribution
6. **Update CHANGELOG** - If CHANGELOG.md exists, updates [Unreleased] section (amends commit)
7. **Push** - Pushes to origin (includes CHANGELOG update)

**Fully automated unless blocked.** No user interaction needed unless there's a problem.

### Example Usage

**Scenario:** You have uncommitted changes and want to commit/push.

```bash
/commitcraft-push
```

**You see analysis output:**

```
================================================================================
GIT PRE-COMMIT ANALYSIS
================================================================================

Generated: 2025-10-23 14:32:15
Repository: /Users/randall/myproject

## Branch & Sync Status
--------------------------------------------------------------------------------
Current branch: feature/auth
Fetching from remote...

## main...origin/main
ℹ️  Your branch is 2 commits AHEAD of remote

## Working Tree Status
--------------------------------------------------------------------------------
Changes detected:

M  src/auth.py
A  tests/test_auth.py

## Changed Files Summary
--------------------------------------------------------------------------------
Staged changes:
 src/auth.py        | 45 +++++++++++++++++++++
 tests/test_auth.py | 32 +++++++++++++++
 2 files changed, 77 insertions(+)

## Security Scan
--------------------------------------------------------------------------------
✓ No obvious secrets detected

## Large Files Check
--------------------------------------------------------------------------------
✓ No unusually large files

## Code Quality Markers
--------------------------------------------------------------------------------
ℹ️  TODO/FIXME markers found:
+    # TODO: Add rate limiting

## Recommended Actions
--------------------------------------------------------------------------------
ℹ️  Stage changes: git add <files>
```

Claude then generates a conventional commit message based on the analysis.

## The commitcraft-analyze.sh Script

### What It Does

Comprehensive pre-commit analysis including:

1. **Branch & Sync Status**
   - Current branch name
   - Detached HEAD warnings
   - Commits ahead/behind remote
   - Remote fetch status

2. **Working Tree Status**
   - Staged changes
   - Unstaged changes
   - Untracked files

3. **Security Scan**
   - Pattern matching for: `password`, `secret`, `api_key`, `token`, `credential`, `private_key`
   - Searches only staged changes
   - Flags suspicious lines for review

4. **Large File Detection**
   - Files with >1000 lines changed
   - Helps catch accidental large commits

5. **Code Quality Markers**
   - Finds `TODO`, `FIXME`, `XXX`, `HACK` comments
   - Only in staged changes

6. **Recent Commit History**
   - Last 5 commits for context

7. **Recommended Actions**
   - Actionable suggestions based on findings

### Running Manually

```bash
# Run in terminal (output to console)
.claude/scripts/commitcraft-analyze.sh

# Save to file for review
.claude/scripts/commitcraft-analyze.sh /tmp/analysis.txt
cat /tmp/analysis.txt

# Use shell alias (if configured)
commitcraft-analyze
```

### Output Format

Structured markdown-style report with clear sections:

- Header with timestamp and repository path
- Section markers with `##` headings
- Visual separators with dashes
- Status indicators: `✓` (good), `⚠️` (warning), `ℹ️` (info)
- Actionable recommendations at end

## Conventional Commit Format

### Structure

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types with Emojis

- `✨ feat` - New feature
- `🐛 fix` - Bug fix
- `📚 docs` - Documentation changes
- `💎 style` - Code style/formatting (no logic changes)
- `♻️ refactor` - Code restructuring (no behavior changes)
- `🧪 test` - Test-related changes
- `🏗️ chore` - Build process/auxiliary tools
- `⚡ perf` - Performance improvements
- `🌱 ci` - CI/CD pipeline changes

### Format Rules

**Scope** (optional):
- Noun describing affected area
- Examples: `auth`, `api`, `parser`, `config`

**Subject**:
- Imperative mood: "Add feature" not "Added feature"
- Maximum 50 characters
- No period at end
- Lowercase after type

**Body**:
- Detailed explanation of changes
- Maximum 72 characters per line
- Blank line separates from subject

**Footer**:
- Breaking changes: `BREAKING CHANGE: description`
- Issue references: `Closes #123`
- Co-authorship (automatically added)

### Examples

```
✨ feat(auth): add OAuth2 login flow

Implements OAuth2 authentication with support for Google and GitHub
providers. Users can now link external accounts and use single sign-on.

- Add OAuth2Controller with callback handling
- Integrate with passport.js middleware
- Add unit tests for token validation

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

```
🐛 fix(parser): handle empty arrays in JSON response

Previously threw TypeError when response.data was empty array.
Now returns early with default values.

Closes #456

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

## Customization

### Per-Repository Customization

Modify `.claude/scripts/commitcraft-analyze.sh` for project-specific checks:

```bash
# Edit local copy
vim .claude/scripts/commitcraft-analyze.sh

# Add custom checks before final section
# Example: pytest collection check
echo "## Test Collection"
echo "--------------------------------------------------------------------------------"
python3 -m pytest --collect-only 2>/dev/null || echo "No tests configured"
echo ""
```

**Other customization ideas:**
- Run linters (eslint, flake8, rubocop)
- Check code coverage requirements
- Validate config files
- Run project-specific security scanners
- Check for license headers

**Important:** Changes only affect current repository. Global template in `~/.claude/` stays unchanged.

### Global Customization

Modify `~/.claude/scripts/commitcraft-analyze.sh` to affect all repos:

```bash
# Edit global template
vim ~/.claude/scripts/commitcraft-analyze.sh

# Add checks that apply to all projects
# Example: Always check for debug statements
echo "## Debug Statements"
echo "--------------------------------------------------------------------------------"
DEBUGS=$(git diff --cached | grep -E "console\.log|debugger|pdb\.set_trace" || true)
if [ -z "$DEBUGS" ]; then
    echo "✓ No debug statements"
else
    echo "⚠️  Debug statements found (remove before commit):"
    echo "$DEBUGS"
fi
```

**After editing global template:**

Re-install in repositories to pick up changes:

```bash
cd myproject
commitcraft-init  # Updates .claude/ from ~/.claude/
```

## Example Scenarios

### Scenario 1: New Project Setup

**Starting point:** Fresh clone, no tools installed

```bash
# Clone repository
git clone https://github.com/example/project.git
cd project

# Make some changes
echo "feature code" >> src/feature.py
git add src/feature.py

# Try to commit via Claude
/commitcraft-push

# See installation prompt
Choose: i (install)

# Tools installed, analysis runs
# Claude generates commit message
# Review and approve

# Result: Clean commit with proper format
```

### Scenario 2: Security Warning

**Starting point:** Added file with API key

```bash
# Add config with secret
echo "API_KEY=sk_live_abc123" >> config.py
git add config.py

# Run commit command
/commitcraft-push

# Analysis detects secret:
⚠️  POTENTIAL SECRETS DETECTED:
+API_KEY=sk_live_abc123

# Claude flags the issue and suggests:
# - Move to environment variables
# - Use .env file with .gitignore
# - Review before proceeding

# You fix the issue before committing
```

### Scenario 3: Behind Remote

**Starting point:** Local branch hasn't pulled recent changes

```bash
# Try to commit
/commitcraft-push

# Analysis shows:
⚠️  Your branch is 3 commits BEHIND remote - consider pulling first

## Recommended Actions
⚠️  Pull remote changes: git pull --rebase origin main

# Claude stops and recommends:
git pull --rebase origin main

# You pull, resolve conflicts, then retry
/commitcraft-push
```

## Troubleshooting

### commitcraft-analyze.sh not found

**Symptom:** Command runs but shows basic analysis only

**Cause:** Tools not installed in current repository

**Fix:**

```bash
# Option 1: Run installer
commitcraft-init

# Option 2: Use full path to global script
~/.claude/scripts/commitcraft-analyze.sh

# Option 3: Check if global tools exist
ls -la ~/.claude/scripts/
# If empty, run global setup
cd ~/Code/AppletScriptorium/CommitCraft
./commitcraft-install.sh
```

### Permission denied errors

**Symptom:** `bash: .claude/scripts/commitcraft-analyze.sh: Permission denied`

**Cause:** Script not executable

**Fix:**

```bash
# Make script executable
chmod +x .claude/scripts/commitcraft-analyze.sh

# Or run with bash explicitly
bash .claude/scripts/commitcraft-analyze.sh
```

### Analysis not showing

**Symptom:** `/commitcraft-push` runs but no analysis output appears

**Cause:** Script failing silently or wrong path

**Fix:**

```bash
# Test script manually
.claude/scripts/commitcraft-analyze.sh

# Check for errors
bash -x .claude/scripts/commitcraft-analyze.sh

# Verify script exists
ls -la .claude/scripts/

# Re-install if missing
commitcraft-init
```

### Command not working as expected

**Symptom:** `/commitcraft-push` doesn't behave as documented

**Cause:** Using old version or custom workflow

**Fix:**

```bash
# Check which file Claude is reading
ls -la .claude/commands/commitcraft-push.md

# Update to latest version
cd ~/Code/AppletScriptorium/CommitCraft
git pull
./commitcraft-install.sh

# Reinstall in repository
cd myproject
rm -rf .claude
commitcraft-init
```

## See Also

- [Main README](/Users/randallnoval/Code/AppletScriptorium/CommitCraft/README.md) - System overview and quick start
- [Adding Tools Guide](/Users/randallnoval/Code/AppletScriptorium/CommitCraft/docs/adding-tools.md) - Create your own commands
- [Shell Aliases](/Users/randallnoval/Code/AppletScriptorium/CommitCraft/shell-aliases) - Useful git shortcuts
