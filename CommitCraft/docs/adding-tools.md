# Adding New Tools to CommitCraft

## Overview

CommitCraft is a multi-tool platform for propagating Claude Code enhancements across all your repositories. The system uses git hooks for discoverability and provides an interactive installation workflow that respects user choice.

**Current tools:**
- Tool #1: Enhanced Git Commit (`/commitcraft-push` + `commitcraft-analyze.sh`)
- Tool #2: (your future tool here)

## File Organization

### Directory Structure

```
CommitCraft/
├── commitcraft-install.sh    # Platform installer
├── commitcraft-init.sh       # Per-repo installer
├── post-checkout             # Git hook
├── your-script.sh            # Your tool script
├── your-command.md           # Your command
├── README.md                 # Platform docs
└── docs/
    ├── your-tool.md          # Your tool docs
    ├── commitcraft-push.md   # Tool #1 docs
    └── adding-tools.md       # This file
```

### Flat Structure

- All scripts and commands live at root (flat structure)
- Detailed docs go in `docs/` directory
- No subdirectories for organization - keeps paths simple

## Adding a New Script

### 1. Create the Script

Place your script at `CommitCraft/your-script.sh`

**Best practices:**
- Use bash shebang: `#!/usr/bin/env bash`
- Add header comments explaining purpose
- Include usage examples
- Make it executable: `chmod +x your-script.sh`

**Example:**

```bash
#!/usr/bin/env bash
# Your Tool Name - Brief description
#
# Usage:
#   ./your-script.sh [options]
#
# Dependencies:
#   - tool1
#   - tool2

set -euo pipefail

# Your code here
```

### 2. Update commitcraft-install.sh

Add your script to the `SOURCE_FILES` array (line 27):

```bash
declare -A SOURCE_FILES=(
    ["~/.claude/scripts/commitcraft-analyze.sh"]="commitcraft-analyze.sh"
    ["~/.claude/scripts/commitcraft-init.sh"]="commitcraft-init.sh"
    ["~/.git-templates/hooks/post-checkout"]="post-checkout"
    ["~/.claude/commands/commitcraft-push.md"]="commitcraft-push.md"
    ["~/.claude/scripts/your-script.sh"]="your-script.sh"  # Add this
)
```

This ensures your script is copied to `~/.claude/scripts/` on install.

### 3. Test Installation

```bash
# Run installer
./commitcraft-install.sh

# Verify file copied
ls -la ~/.claude/scripts/your-script.sh

# Test execution
~/.claude/scripts/your-script.sh
```

## Adding a New Command

### 1. Create the Command File

Place your command at `CommitCraft/your-command.md`

**Follow Claude Code slash command best practices:**
- Add frontmatter with description and allowed-tools
- Keep it simple (complex workflows should be Skills)
- Single-purpose and frequently-used
- Check for `.claude/` directory and prompt for installation if missing

**Example structure:**

```markdown
---
description: "Brief description of your command"
allowed-tools: ["Bash", "Read", "Edit"]
---

# Your Command Name

## Workflow

1. Check if tools are installed:
   ```bash
   if [ ! -d .claude ]; then
       # Show installation prompt
       echo "Claude Code tools not installed in this repo."
       echo ""
       echo "Would you like to install them? They enable:"
       echo "  - your-script.sh (feature description)"
       echo "  - Enhanced workflows"
       echo ""
       echo "Choose:"
       echo "  i - Install tools in .claude/"
       echo "  n - Never ask again (ignore)"
       echo "  d - Defer (ask later)"
       # Handle user choice
   fi
   ```

2. Execute your workflow steps...
```

### 2. Update commitcraft-install.sh

Add your command to `SOURCE_FILES` array (line 27):

```bash
["~/.claude/commands/your-command.md"]="your-command.md"
```

This ensures your command is copied to `~/.claude/commands/` on install.

### 3. Test Command

```bash
# Run installer
./commitcraft-install.sh

# Verify file copied
ls -la ~/.claude/commands/your-command.md

# Test in Claude Code
# Use /your-command in a repository
```

## Adding Documentation

### 1. Create Tool Documentation

Create `docs/your-tool.md` with:

- Overview and purpose
- Installation instructions
- Usage examples
- Customization options
- Troubleshooting section

**Example structure:**

```markdown
# Tool Name

## Overview

Brief description of what your tool does and why it's useful.

## Installation

Covered by main commitcraft-install.sh - automatically included.

## Usage

### Basic Usage

```bash
# Example command
your-script.sh arg1 arg2
```

### Advanced Usage

```bash
# Example with options
your-script.sh --option value
```

## Customization

How to customize per-repo or globally.

## Troubleshooting

Common issues and solutions.
```

### 2. Update README.md

Add your tool to the "Available Tools" section (after line 89):

```markdown
### Tool #2: Your Tool Name (/your-command)

**Brief:** One-line description of what your tool does.

**Scripts:**
- `your-script.sh` - Brief script description

**Commands:**
- `/your-command` - Brief command description

**Key features:**
- Feature 1
- Feature 2
- Feature 3

**Detailed documentation:** See [docs/your-tool.md](/Users/randallnoval/Code/AppletScriptorium/CommitCraft/docs/your-tool.md)
```

## Testing

### 1. Test Installation

```bash
# Run installer
cd /Users/randallnoval/Code/AppletScriptorium/CommitCraft
./commitcraft-install.sh

# Verify files copied to global location
ls -la ~/.claude/scripts/your-script.sh
ls -la ~/.claude/commands/your-command.md

# Check permissions
test -x ~/.claude/scripts/your-script.sh && echo "Executable" || echo "Not executable"
```

### 2. Test in Repository

```bash
# Create test repo
cd /tmp
mkdir test-repo
cd test-repo
git init

# Install tools locally
claude-init

# Verify local installation
ls -la .claude/scripts/your-script.sh

# Test command in Claude Code
# Use /your-command
```

### 3. Test Updates

```bash
# Modify source file
cd /Users/randallnoval/Code/AppletScriptorium/CommitCraft
echo "# updated comment" >> your-script.sh

# Run installer again
./commitcraft-install.sh

# Should show "update available" and offer to update
# Accept update and verify changes propagated
cat ~/.claude/scripts/your-script.sh | tail -1
```

### 4. Test Hash-Based Detection

```bash
# Touch file (change timestamp only)
touch your-script.sh

# Run installer
./commitcraft-install.sh

# Should show "up to date" (hash unchanged)
# This validates content-based detection works
```

## Best Practices

### Naming Conventions

- **Scripts:** kebab-case (e.g., `commitcraft-analyze.sh`)
- **Commands:** kebab-case (e.g., `git-push.md`)
- **Docs:** kebab-case (e.g., `docs/commitcraft-push.md`)

### Script Standards

- Always use `set -euo pipefail` for safety
- Include usage examples in header comments
- Handle errors gracefully with clear messages
- Make scripts executable before committing

### Command Standards

- Always check for `.claude/` directory
- Provide installation prompt when tools missing
- Support three choices: Install / Ignore / Defer
- Provide fallback behavior when possible

### Documentation

- Always create detailed docs in `docs/` directory
- Keep README.md brief (catalog only)
- Include troubleshooting section
- Provide concrete usage examples

### Hash-Based Updates

- The installer uses MD5 hashes to detect changes
- Timestamp-independent (works reliably with git pull)
- No need to manually track versions
- Content changes automatically detected

## Complete Example: Adding a Log Analyzer

**Step 1: Create script**

```bash
cd /Users/randallnoval/Code/AppletScriptorium/CommitCraft

cat > analyze-logs.sh << 'EOF'
#!/usr/bin/env bash
# Log Analyzer - Extracts error patterns from logs
#
# Usage:
#   analyze-logs.sh <logfile>

set -euo pipefail

logfile="${1:-}"
if [ -z "$logfile" ]; then
    echo "Usage: analyze-logs.sh <logfile>"
    exit 1
fi

# Extract errors
grep -i "error\|warning" "$logfile" | sort | uniq -c | sort -rn
EOF

chmod +x analyze-logs.sh
```

**Step 2: Create command**

```bash
cat > analyze-logs.md << 'EOF'
---
description: "Analyze logs for error patterns"
allowed-tools: ["Bash", "Read"]
---

# Analyze Logs

Check if tools installed, run analysis...
EOF
```

**Step 3: Update commitcraft-install.sh**

```bash
# Edit line 27, add:
["~/.claude/scripts/analyze-logs.sh"]="analyze-logs.sh"
["~/.claude/commands/analyze-logs.md"]="analyze-logs.md"
```

**Step 4: Create documentation**

```bash
cat > docs/analyze-logs.md << 'EOF'
# Log Analyzer

Extracts error patterns from log files...
EOF
```

**Step 5: Update README.md**

Add tool description to "Available Tools" section.

**Step 6: Test**

```bash
# Install
./commitcraft-install.sh

# Test in repo
cd /tmp/test-repo
claude-init
.claude/scripts/analyze-logs.sh /var/log/system.log
```

## See Also

- Main README.md - Platform overview and usage
- docs/commitcraft-push.md - Example tool implementation
- commitcraft-install.sh - Source code for installer logic
