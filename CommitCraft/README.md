# CommitCraft

A lightweight, git-based system for propagating CommitCraft tools and enhancements across all your repositories without intrusion or forced installs.

## Overview

When you develop useful CommitCraft scripts and workflows (git commit analysis, project initialization helpers, custom commands), you want them available across all your projects. But copying files manually is tedious, and auto-installation removes user choice.

This system solves the discoverability problem through git hooks that passively remind you about available tools when you clone or work in repositories. When you first use a command like `/commitcraft-push` (git commit workflow), you get an interactive prompt: install the tools, ignore them permanently, or defer the decision. Your choice is remembered per-repository.

**Key benefits:**

- Non-intrusive: Passive reminders, not forced installs
- User agency: You choose install/ignore/defer on first use
- Works everywhere: Git hooks run automatically in all repos after one-time setup
- Template-based: This repo provides a reference implementation you can customize

## Quick Start

```bash
# Clone this repository
git clone https://github.com/starfysh-tech/AppletScriptorium.git
cd AppletScriptorium/CommitCraft

# Run the intelligent installer
./commitcraft-install.sh
```

**The installer automatically detects your current state:**
- **Not installed:** Offers to install hooks and tools
- **Updates available:** Shows what changed, offers to update
- **Up to date:** Confirms all files current

Uses content hashing (MD5) for accurate change detection—works reliably after `git pull`.

After setup, the system activates automatically in all git repositories:

- Passive reminders appear after `git checkout` or `git clone`
- Interactive prompts appear when you use commands like `/commitcraft-push`
- Your choices are saved per-repository

## How It Works

The system uses a three-tier architecture:

**1. Global Tools (~/.claude/)**
- Your personal CommitCraft toolkit
- Contains scripts like `commitcraft-analyze.sh`
- Installed once, available everywhere

**2. Git Hook Templates (~/.git-templates/hooks/)**
- Git hooks that run automatically in all repos
- `post-checkout`: Shows passive reminder after clone/checkout
- Triggers interactive prompts when commands detect missing tools

**3. Local Tools (.claude/)**
- Repository-specific copies of global tools
- Created when you choose "Install" at the prompt
- Can be customized per-project

**Flow:**

1. Git hook runs after checkout/clone
2. Checks if `.claude/` exists or `.claude-ignore` present
3. If neither, shows passive reminder (once per repo)
4. When you use `/commitcraft-push` or similar command:
   - Detects missing `.claude/` directory
   - Prompts: Install / Ignore / Defer
   - Your choice is saved (.claude/ created or .claude-ignore added to .git/info/exclude)

## Available Tools

### Tool #1: Enhanced Git Commit (/commitcraft-push command)

**Brief:** AI-assisted commits with security scanning, conventional format, and rich context analysis.

**Scripts:**
- `commitcraft-analyze.sh` - Gathers commit context (status, diffs, secrets, TODOs, file tree)

**Commands:**
- `/commitcraft-push` - Interactive git commit workflow with AI assistance

**Key features:**
- Automated secret scanning before commit
- Conventional commit format enforcement
- Rich context gathering for AI-generated messages
- Interactive review and approval workflow

**Detailed documentation:** See [docs/commitcraft-push.md](/Users/randallnoval/Code/AppletScriptorium/CommitCraft/docs/commitcraft-push.md)

### commitcraft-init

Command-line tool to install CommitCraft tools in the current repository:

```bash
# Install tools
commitcraft-init

# Creates:
# .claude/scripts/commitcraft-analyze.sh
# .claude/scripts/commitcraft-init.sh
# Updates .gitignore to exclude .claude/
```

Available via shell alias after running `commitcraft-install.sh`.

## Using in New Repos

### First Clone

```bash
# Clone any repository
git clone https://github.com/example/project.git
cd project

# You see a passive reminder:
# 📎 CommitCraft tools are available via `commitcraft-init`. Run anytime to install.
```

### First Command Use

```bash
# Try using a command in CommitCraft
/commitcraft-push "Add user authentication"

# You see an interactive prompt:
# CommitCraft tools not installed in this repo.
#
# Would you like to install them? They enable:
#   - commitcraft-analyze.sh (commit context)
#   - Enhanced workflows
#
# Choose:
#   i - Install tools in .claude/
#   n - Never ask again (ignore)
#   d - Defer (ask later)
#
# Your choice:
```

**After choosing "Install":**
- `.claude/` directory created with scripts
- `.claude/` added to `.gitignore` (tools stay local)
- Commands work seamlessly

**After choosing "Ignore":**
- `.claude-ignore` marker added to `.git/info/exclude`
- Commands use fallback behavior (work without tools)
- Never prompted again in this repo

**After choosing "Defer":**
- Nothing changes
- Prompted again next time you use the command

## Using in Existing Repos

For repositories that existed before you installed the hooks:

### Automatic Activation

```bash
cd existing-project

# Next time you checkout a branch:
git checkout feature-branch

# You see the passive reminder:
# 📎 CommitCraft tools are available via `commitcraft-init`. Run anytime to install.
```

### Manual Installation

```bash
cd existing-project

# Run the installer directly
commitcraft-init

# Tools installed in .claude/
```

### Opt-Out

To permanently ignore tools in a specific repo:

```bash
# Create the ignore marker
touch .git/info/exclude
echo '.claude-ignore' >> .git/info/exclude
touch .claude-ignore

# Or just answer "n" when prompted by a command
```

## Adding New Tools

This system is designed for extension. To add new tools:

**Quick steps:**

1. Create your script in `CommitCraft/scripts/`
2. Update `SOURCE_FILES` array in `commitcraft-install.sh`
3. Run `./commitcraft-install.sh` to propagate to `~/.claude/`
4. Create command template that checks for `.claude/` and prompts for installation

**Detailed documentation:** See [docs/adding-tools.md](/Users/randallnoval/Code/AppletScriptorium/CommitCraft/docs/adding-tools.md)

## Customization

### Per-Repo Scripts

After installing tools in a repo, customize them locally:

```bash
cd myproject

# Edit local copy
vim .claude/scripts/commitcraft-analyze.sh

# Changes only affect this repo
# Global template (~/.claude/) stays unchanged
```

### Updating Global Baseline

To pull latest versions from AppletScriptorium:

```bash
cd AppletScriptorium/CommitCraft
git pull

# Re-run installer—it detects what's changed
./commitcraft-install.sh
```

**The installer shows you exactly what changed:**
- Lists files with updates available
- Uses content hashing to detect real changes (not timestamps)
- Offers to update all or skip

**After updating `~/.claude/`:**

To propagate updates to existing repos:

```bash
# Re-run commitcraft-init in each repo
cd myproject
commitcraft-init  # Updates .claude/ with latest from ~/.claude/
```

## Troubleshooting

### Hook Not Running

**Symptom:** No passive reminder after `git clone` or `git checkout`

**Fixes:**

```bash
# Verify hooks are installed globally
ls -la ~/.git-templates/hooks/

# Should see: post-checkout

# Verify git is configured to use templates
git config --global init.templateDir
# Should output: ~/.git-templates

# Re-run setup if needed
cd AppletScriptorium/CommitCraft
./commitcraft-install.sh

# For existing repos, manually copy hooks
mkdir -p .git/hooks
cp ~/.git-templates/hooks/post-checkout .git/hooks/
chmod +x .git/hooks/post-checkout
```

### Tools Not Installing

**Symptom:** `commitcraft-init` command not found or fails

**Fixes:**

```bash
# Verify global tools exist
ls -la ~/.claude/scripts/

# Should see: commitcraft-init.sh, commitcraft-analyze.sh

# Option 1: Use shell alias (if you added it during install)
commitcraft-init

# Option 2: Use full path (always works)
~/.claude/scripts/commitcraft-init.sh

# Option 3: Add to PATH
echo 'export PATH="$HOME/.claude/scripts:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Verify permissions
chmod +x ~/.claude/scripts/*
```

### Shell Alias Not Working

**Symptom:** `commitcraft-init` command not found after install

**Cause:** Shell aliases are optional during installation

**Fixes:**

```bash
# Option 1: Re-run installer
cd AppletScriptorium/CommitCraft
./commitcraft-install.sh

# Option 2: Add alias manually to your shell config
echo "alias commitcraft-init='~/.claude/scripts/commitcraft-init.sh'" >> ~/.zshrc
source ~/.zshrc

# Option 3: Just use the full path (no alias needed)
~/.claude/scripts/commitcraft-init.sh
```

### Reset/Uninstall

**Remove from specific repo:**

```bash
cd myproject

# Remove tools
rm -rf .claude

# Remove ignore marker
rm .claude-ignore
# Also remove from .git/info/exclude if added manually
```

**Uninstall completely:**

```bash
# Remove global tools
rm -rf ~/.claude

# Remove git hook templates
rm -rf ~/.git-templates/hooks

# Remove git configuration
git config --global --unset init.templateDir

# Existing repos keep their hooks
# To remove from existing repo:
rm .git/hooks/post-checkout
```

**Clean reinstall:**

```bash
# Uninstall (steps above)
# Then re-run setup
cd AppletScriptorium/CommitCraft
./commitcraft-install.sh
```

## Philosophy

This system respects user agency:

- **Passive, not aggressive:** Reminders, not auto-installs
- **Choice preserved:** Install/ignore/defer on your terms
- **Transparent:** Plain shell scripts, no magic
- **Customizable:** Modify per-repo or globally

The goal is discoverability without intrusion. You control when and where CommitCraft enhancements are used.
