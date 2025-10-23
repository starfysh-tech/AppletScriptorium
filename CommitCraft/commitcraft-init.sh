#!/usr/bin/env bash
# CommitCraft Installer
#
# Installs CommitCraft enhancement tools in the current repository
# Copies scripts and commands from global ~/.claude/ to local .claude/
#
# Usage: commitcraft-init (run from within a git repository)

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get repository root
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$REPO_ROOT" ]; then
    echo "❌ Not a git repository"
    echo "   Run this command from within a git repo"
    exit 1
fi

echo -e "${BLUE}🤖 Installing CommitCraft tools${NC}"
echo "   Repository: $REPO_ROOT"
echo ""

# Create directory structure
mkdir -p "$REPO_ROOT/.claude/scripts"
mkdir -p "$REPO_ROOT/.claude/commands"

# Track what was installed
INSTALLED_COUNT=0

# Copy scripts from global (allow list only scripts needed by commands)
if [ -d ~/.claude/scripts ]; then
    # Only copy scripts that local commands actually use
    for SCRIPT_NAME in "commitcraft-analyze.sh"; do
        local script="~/.claude/scripts/$SCRIPT_NAME"
        local DEST="$REPO_ROOT/.claude/scripts/$SCRIPT_NAME"

        if [ -f "$script" ]; then
            # Use -n flag to prevent overwriting (no-clobber)
            if cp -n "$script" "$DEST" 2>/dev/null; then
                echo -e "${GREEN}✓${NC} Installed script: $SCRIPT_NAME"
                ((INSTALLED_COUNT++))
            else
                echo -e "${YELLOW}⊘${NC} Skipped $SCRIPT_NAME (already exists, preserving local version)"
            fi
        else
            echo -e "${RED}✗${NC} Script not found in global: $SCRIPT_NAME"
        fi
    done
fi

# Copy commands from global (allow list only CommitCraft commands)
if [ -d ~/.claude/commands ]; then
    # Only copy CommitCraft-specific commands
    for COMMAND_NAME in "commitcraft-push.md"; do
        local command="~/.claude/commands/$COMMAND_NAME"
        local DEST="$REPO_ROOT/.claude/commands/$COMMAND_NAME"

        if [ -f "$command" ]; then
            # Use -n flag to prevent overwriting (no-clobber)
            if cp -n "$command" "$DEST" 2>/dev/null; then
                echo -e "${GREEN}✓${NC} Installed command: $COMMAND_NAME"
                ((INSTALLED_COUNT++))
            else
                echo -e "${YELLOW}⊘${NC} Skipped $COMMAND_NAME (already exists, preserving local version)"
            fi
        else
            echo -e "${RED}✗${NC} Command not found in global: $COMMAND_NAME"
        fi
    done
fi

# Create local README (only if it doesn't exist - preserve customizations)
if [ ! -f "$REPO_ROOT/.claude/README.md" ]; then
    cat > "$REPO_ROOT/.claude/README.md" << 'EOF'
# CommitCraft

This directory contains CommitCraft enhancements for this repository.

## Local Customization

You can customize scripts in `.claude/scripts/` for repo-specific behavior.
For example, add project-specific checks to `commitcraft-analyze.sh`:

```bash
# Add pytest check
echo -e "\n## Test Status"
python3 -m pytest --collect-only 2>/dev/null || echo "No tests"
```

## Update from Global

To pull latest versions from your global tools:

```bash
commitcraft-init  # Re-run to refresh
```

## Opt-out

To remove CommitCraft tools from this repo:

```bash
rm -rf .claude && touch .claude-ignore
```

## Available Scripts

- `commitcraft-analyze.sh` - Gathers commit context for `/commitcraft-push` command
- Add your own scripts here

## Available Commands

- See `.claude/commands/` for available slash commands
- Add custom commands by creating `.md` files

---

Installed from: ~/.claude/
EOF
fi

echo ""
if [ $INSTALLED_COUNT -eq 0 ]; then
    echo -e "${YELLOW}⚠${NC}  No tools found in ~/.claude/"
    echo "   Run the global setup first:"
    echo "   ./CommitCraft/commitcraft-install.sh"
else
    echo -e "${GREEN}✅ Installation complete${NC}"
    echo "   Installed $INSTALLED_COUNT files"
    echo ""
    echo "Next steps:"
    echo "  - Customize scripts in .claude/scripts/ for this repo"
    echo "  - Add .claude/ to .gitignore if you want user-specific tools"
    echo "  - Or commit .claude/ to share tools with team"
fi

exit 0
