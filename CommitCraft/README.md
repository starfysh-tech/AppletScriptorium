# CommitCraft

Development workflow enhancement toolkit. Provides git commit analysis with security scanning, conventional format enforcement, and automated release management.

## Overview

CommitCraft provides tools that enhance your development workflow across all repositories:

- **Commit Analysis** - Security scanning, large file detection, sync checking
- **Automated Commits** - AI-assisted commit messages with conventional format
- **Release Automation** - Semantic versioning with auto-generated release notes

**Key benefits:**

- Single-step global setup works in all repositories
- No per-repo configuration needed
- Commands available immediately after installation
- Scripts stay in `~/.claude/` - no local copies to maintain

## Quick Start

```bash
# Clone this repository
git clone https://github.com/starfysh-tech/AppletScriptorium.git
cd AppletScriptorium/CommitCraft

# Run the installer
./commitcraft-install.sh
```

**The installer automatically detects your current state:**
- **Not installed:** Offers to install tools to `~/.claude/`
- **Updates available:** Shows what changed, offers to update
- **Up to date:** Confirms all files current

Uses content hashing (MD5) for accurate change detection—works reliably after `git pull`.

After setup, CommitCraft commands work immediately in any git repository.

## How It Works

CommitCraft uses a simple 2-tier architecture:

**1. Global Tools (~/.claude/)**
- Scripts installed to `~/.claude/scripts/`
- Commands installed to `~/.claude/commands/`
- Works in all repositories automatically

**2. Commands Reference Scripts**
- Commands like `/commitcraft-push` run scripts from `~/.claude/scripts/`
- No local installation or configuration needed
- Works in any directory

**Flow:**

1. Run `./commitcraft-install.sh` once (copies files to `~/.claude/`)
2. Commands immediately available in Claude Code (any repo)
3. Scripts run from global location using current working directory

## Available Tools

### /commitcraft-push Command

**Brief:** Automated git commit workflow with security scanning and AI-assisted messaging.

**What it does:**
1. Runs `commitcraft-analyze.sh` for context (security, diffs, sync status)
2. Checks for blockers (secrets, behind remote, conflicts)
3. Auto-stages all changes
4. Generates conventional commit message with Claude
5. Auto-commits with attribution
6. Auto-pushes to origin

**Blockers (stops only for these):**
- 🛑 Potential secrets detected
- 🛑 Branch behind remote (need pull first)
- 🛑 Merge conflicts present
- 🛑 Large files (>1000 lines changed)

**Otherwise fully automated** - no user interaction needed.

**Detailed documentation:** See [docs/commitcraft-push.md](docs/commitcraft-push.md)

---

### /commitcraft-release Command

**Brief:** Automated semantic versioning and GitHub release creation.

**What it does:**
1. Runs `commitcraft-release-analyze.sh` for version analysis
2. Checks for blockers (dirty tree, no gh CLI, no commits)
3. Auto-detects version bump from conventional commits
4. Generates structured release notes
5. Creates git tag
6. Pushes tag to origin
7. Creates GitHub release

**Version bump rules:**
- **BREAKING CHANGE** in commits → major (v2.0.0 → v3.0.0)
- **feat:** commits → minor (v2.0.0 → v2.1.0)
- **fix:** commits → patch (v2.0.0 → v2.0.1)

**Blockers (stops only for these):**
- 🛑 Uncommitted changes
- 🛑 GitHub CLI not installed/authenticated
- 🛑 No commits since last release

**Otherwise fully automated** - no user interaction needed.

---

### commitcraft-analyze.sh Script

**Brief:** Pre-commit analysis for security and quality checks.

**What it does:**
- Scans for potential secrets (API keys, passwords, tokens)
- Detects large file changes (>1000 lines)
- Checks sync status with remote
- Surfaces TODO/FIXME markers in changes
- Provides context for AI commit message generation

**Usage:**
```bash
# Via alias (if configured)
git-analyze

# Or directly
~/.claude/scripts/commitcraft-analyze.sh
```

**Used by:** `/commitcraft-push` command

---

### commitcraft-release-analyze.sh Script

**Brief:** Release analysis for semantic versioning.

**What it does:**
- Validates gh CLI availability and authentication
- Checks for clean working tree
- Parses latest semver tag
- Categorizes commits by type (breaking/feat/fix/docs)
- Calculates version bump
- Displays structured analysis

**Usage:**
```bash
~/.claude/scripts/commitcraft-release-analyze.sh
```

**Used by:** `/commitcraft-release` command

## Installation Details

### What Gets Installed

```
~/.claude/
├── scripts/
│   ├── commitcraft-analyze.sh
│   └── commitcraft-release-analyze.sh
└── commands/
    ├── commitcraft-push.md
    └── commitcraft-release.md
```

### Shell Aliases (Optional)

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
# Run global setup
alias claude-setup='~/Code/AppletScriptorium/CommitCraft/commitcraft-install.sh'

# Run pre-commit analysis
alias git-analyze='~/.claude/scripts/commitcraft-analyze.sh'
```

See [shell-aliases](shell-aliases) for complete set of convenience aliases.

## Using Commands

### In Any Repository

```bash
cd any-project

# Use CommitCraft commands immediately
/commitcraft-push
/commitcraft-release

# Or run scripts directly
~/.claude/scripts/commitcraft-analyze.sh
```

**No per-repo setup needed.** Commands work in any git repository after global installation.

## Updating

### Update Global Toolkit

```bash
cd AppletScriptorium/CommitCraft
git pull

# Re-run installer - shows what changed
./commitcraft-install.sh
```

The installer uses content hashing to detect changes and shows exactly which files have updates available.

### No Per-Repo Updates Needed

Since commands reference `~/.claude/scripts/` directly, all repositories use the latest versions automatically after updating global installation.

## Adding New Tools

This system is designed for extension. To add new tools:

**Steps:**

1. Create script in `CommitCraft/` (e.g., `my-tool.sh`)
2. Create command in `CommitCraft/` (e.g., `my-command.md`)
3. Update `SOURCE_FILES` array in `commitcraft-install.sh`:
   ```bash
   declare -A SOURCE_FILES=(
       # ... existing files ...
       ["~/.claude/scripts/my-tool.sh"]="my-tool.sh"
       ["~/.claude/commands/my-command.md"]="my-command.md"
   )
   ```
4. Run `./commitcraft-install.sh` to propagate to `~/.claude/`
5. Command immediately available in all repos

**Command pattern:**
```bash
# Commands should reference global scripts
~/.claude/scripts/my-tool.sh
```

**Detailed documentation:** See [docs/adding-tools.md](docs/adding-tools.md)

## Troubleshooting

### Commands Not Found

**Symptom:** `/commitcraft-push` not recognized in Claude Code

**Fixes:**

```bash
# Verify commands installed globally
ls -la ~/.claude/commands/

# Should see: commitcraft-push.md, commitcraft-release.md

# Re-run installer if missing
cd AppletScriptorium/CommitCraft
./commitcraft-install.sh
```

### Scripts Not Found

**Symptom:** Command fails with "script not found" error

**Fixes:**

```bash
# Verify scripts installed globally
ls -la ~/.claude/scripts/

# Should see: commitcraft-analyze.sh, commitcraft-release-analyze.sh

# Verify permissions
chmod +x ~/.claude/scripts/*

# Re-run installer if needed
cd AppletScriptorium/CommitCraft
./commitcraft-install.sh
```

### Shell Alias Not Working

**Symptom:** `git-analyze` command not found

**Cause:** Shell aliases are optional

**Fixes:**

```bash
# Option 1: Add alias manually
echo "alias git-analyze='~/.claude/scripts/commitcraft-analyze.sh'" >> ~/.zshrc
source ~/.zshrc

# Option 2: Use full path (no alias needed)
~/.claude/scripts/commitcraft-analyze.sh

# Option 3: Add to PATH
echo 'export PATH="$HOME/.claude/scripts:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Uninstall

**Remove global tools:**

```bash
# Remove all CommitCraft files
rm -rf ~/.claude

# Verify removal
ls -la ~/.claude
```

**Clean reinstall:**

```bash
# Uninstall (step above)
# Then re-run setup
cd AppletScriptorium/CommitCraft
./commitcraft-install.sh
```

## Philosophy

This system prioritizes simplicity:

- **Single setup** - Install once, use everywhere
- **No per-repo config** - Works in any repository immediately
- **Transparent** - Plain shell scripts, no magic
- **Updateable** - One command updates all repositories

The goal is to provide useful development tools without complexity or maintenance burden.
