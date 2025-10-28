# Adding New Tools to CommitCraft

## Overview

CommitCraft is a development workflow enhancement toolkit. Tools are simple: create a script, create a command that uses it, and add both to the installer. After running the installer, the command works in any repository.

**Current tools:**
- Tool #1: Automated Commits (`/commitcraft-push` + `commitcraft-analyze.sh`)
- Tool #2: Automated Releases (`/commitcraft-release` + `commitcraft-release-analyze.sh`)
- Tool #3: (your future tool here)

## File Organization

### Directory Structure

```
CommitCraft/
├── commitcraft-install.sh          # Global installer
├── commitcraft-analyze.sh          # Tool #1 script
├── commitcraft-release-analyze.sh  # Tool #2 script
├── commitcraft-push.md             # Tool #1 command
├── commitcraft-release.md          # Tool #2 command
├── your-tool.sh                    # Your script
├── your-command.md                 # Your command
├── README.md                       # Platform docs
└── docs/
    ├── commitcraft-push.md         # Tool #1 docs
    ├── adding-tools.md             # This file
    └── your-tool.md                # Your tool docs
```

### Flat Structure

- All scripts and commands live at root (flat structure)
- Detailed docs go in `docs/` directory
- No subdirectories for organization - keeps paths simple

## Adding a New Script

### 1. Create the Script

Place your script at `CommitCraft/your-tool.sh`

**Best practices:**
- Use bash shebang: `#!/usr/bin/env bash`
- Add header comments explaining purpose
- Include usage examples
- Make it executable: `chmod +x your-tool.sh`

**Example:**

```bash
#!/usr/bin/env bash
# Your Tool Name - Brief description
#
# Usage:
#   your-tool.sh [options]
#
# Dependencies:
#   - tool1
#   - tool2

set -euo pipefail

# Your code here
```

### 2. Update commitcraft-install.sh

Add your script to the `SOURCE_FILES` array (around line 27):

```bash
declare -A SOURCE_FILES=(
    ["~/.claude/scripts/commitcraft-analyze.sh"]="commitcraft-analyze.sh"
    ["~/.claude/scripts/commitcraft-release-analyze.sh"]="commitcraft-release-analyze.sh"
    ["~/.claude/commands/commitcraft-push.md"]="commitcraft-push.md"
    ["~/.claude/commands/commitcraft-release.md"]="commitcraft-release.md"
    ["~/.claude/scripts/your-tool.sh"]="your-tool.sh"  # Add this
)
```

This ensures your script is copied to `~/.claude/scripts/` on install.

### 3. Test Installation

```bash
# Run installer
./commitcraft-install.sh

# Verify file copied
ls -la ~/.claude/scripts/your-tool.sh

# Test execution
~/.claude/scripts/your-tool.sh
```

## Adding a New Command

### 1. Create the Command File

Place your command at `CommitCraft/your-command.md`

**Follow Claude Code slash command best practices:**
- Add frontmatter with description and allowed-tools
- Keep it simple (complex workflows should be Skills)
- Single-purpose and frequently-used
- Reference scripts from `~/.claude/scripts/` (global location)

**Example structure:**

```markdown
---
description: "Brief description of your command"
allowed-tools: ["Bash", "Read", "Edit"]
---

# Your Command Name

Brief description and purpose.

## Workflow

### Step 1: Run Analysis

Execute your script from global location:
```bash
~/.claude/scripts/your-tool.sh
```

### Step 2: Process Results

Handle output and take action...

### Step 3: Report Success

Show results to user.
```

**Key point:** Commands reference `~/.claude/scripts/` directly - no local installation needed.

### 2. Update commitcraft-install.sh

Add your command to `SOURCE_FILES` array:

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
# Use /your-command in any repository
```

## Adding Documentation

### 1. Create Tool Documentation

Create `docs/your-tool.md` with:

- Overview and purpose
- Usage examples
- Customization options
- Troubleshooting section

**Example structure:**

```markdown
# Tool Name

## Overview

Brief description of what your tool does and why it's useful.

## Installation

Included automatically when running `./commitcraft-install.sh`.

Installed to:
- Script: `~/.claude/scripts/your-tool.sh`
- Command: `~/.claude/commands/your-command.md`

## Usage

### Basic Usage

```bash
# Via command
/your-command

# Or directly
~/.claude/scripts/your-tool.sh arg1 arg2
```

### Advanced Usage

```bash
# Example with options
~/.claude/scripts/your-tool.sh --option value
```

## Troubleshooting

Common issues and solutions.
```

### 2. Update README.md

Add your tool to the "Available Tools" section:

```markdown
### /your-command Command

**Brief:** One-line description of what your tool does.

**What it does:**
1. Step 1 description
2. Step 2 description
3. Step 3 description

**Blockers (stops only for these):**
- 🛑 Problem 1
- 🛑 Problem 2

**Otherwise fully automated** - no user interaction needed.

---

### your-tool.sh Script

**Brief:** One-line script description.

**What it does:**
- Feature 1
- Feature 2
- Feature 3

**Usage:**
```bash
~/.claude/scripts/your-tool.sh
```

**Used by:** `/your-command` command
```

## Testing

### 1. Test Installation

```bash
# Run installer
cd ~/Code/AppletScriptorium/CommitCraft
./commitcraft-install.sh

# Verify files copied to global location
ls -la ~/.claude/scripts/your-tool.sh
ls -la ~/.claude/commands/your-command.md

# Check permissions
test -x ~/.claude/scripts/your-tool.sh && echo "Executable" || echo "Not executable"
```

### 2. Test in Any Repository

```bash
# Navigate to any git repository
cd ~/some-other-project

# Test script directly
~/.claude/scripts/your-tool.sh

# Test command in Claude Code
# Use /your-command
```

**No per-repo setup needed** - scripts work from global location.

### 3. Test Updates

```bash
# Modify source file
cd ~/Code/AppletScriptorium/CommitCraft
echo "# updated comment" >> your-tool.sh

# Run installer again
./commitcraft-install.sh

# Should show "update available" and offer to update
# Accept update and verify changes propagated
cat ~/.claude/scripts/your-tool.sh | tail -1
```

### 4. Test Hash-Based Detection

```bash
# Touch file (change timestamp only)
touch your-tool.sh

# Run installer
./commitcraft-install.sh

# Should show "up to date" (hash unchanged)
# This validates content-based detection works
```

## Best Practices

### Naming Conventions

- **Scripts:** `commitcraft-*` prefix, kebab-case (e.g., `commitcraft-analyze.sh`)
- **Commands:** `commitcraft-*` prefix, kebab-case (e.g., `commitcraft-push.md`)
- **Docs:** Match tool name (e.g., `docs/commitcraft-push.md`)

### Script Standards

- Always use `set -euo pipefail` for safety
- Include usage examples in header comments
- Handle errors gracefully with clear messages
- Make scripts executable before committing
- Test with various working directories (scripts run from `~/.claude/scripts/` but operate on `$PWD`)

### Command Standards

- Reference scripts from `~/.claude/scripts/` (not `.claude/scripts/`)
- Focus on automation - only stop for blockers
- Provide clear blocker messages with resolution steps
- Report success clearly at the end

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
cd ~/Code/AppletScriptorium/CommitCraft

cat > commitcraft-logs.sh << 'EOF'
#!/usr/bin/env bash
# Log Analyzer - Extracts error patterns from logs
#
# Usage:
#   commitcraft-logs.sh <logfile>

set -euo pipefail

logfile="${1:-}"
if [ -z "$logfile" ]; then
    echo "Usage: commitcraft-logs.sh <logfile>"
    exit 1
fi

# Extract errors
grep -i "error\|warning" "$logfile" | sort | uniq -c | sort -rn
EOF

chmod +x commitcraft-logs.sh
```

**Step 2: Create command**

```bash
cat > commitcraft-logs.md << 'EOF'
---
description: "Analyze logs for error patterns"
allowed-tools: ["Bash", "Read"]
---

# Analyze Logs

Extracts and counts error patterns from log files.

## Workflow

### Step 1: Find log files

Locate log files in current directory:
```bash
find . -name "*.log" -type f
```

### Step 2: Analyze

Run analysis on each file:
```bash
~/.claude/scripts/commitcraft-logs.sh <logfile>
```

### Step 3: Report

Show top error patterns to user.
EOF
```

**Step 3: Update commitcraft-install.sh**

```bash
# Edit SOURCE_FILES array, add:
["~/.claude/scripts/commitcraft-logs.sh"]="commitcraft-logs.sh"
["~/.claude/commands/commitcraft-logs.md"]="commitcraft-logs.md"
```

**Step 4: Create documentation**

```bash
cat > docs/commitcraft-logs.md << 'EOF'
# Log Analyzer

Extracts error patterns from log files.

## Installation

Installed automatically via `./commitcraft-install.sh`.

## Usage

```bash
# Via command
/commitcraft-logs

# Or directly
~/.claude/scripts/commitcraft-logs.sh /var/log/system.log
```
EOF
```

**Step 5: Update README.md**

Add tool description to "Available Tools" section.

**Step 6: Test**

```bash
# Install
./commitcraft-install.sh

# Test in any repo
cd ~/some-project
~/.claude/scripts/commitcraft-logs.sh app.log
```

## Architecture Notes

### Why Global Scripts?

Commands reference `~/.claude/scripts/` directly because:

1. **Simplicity** - No per-repo installation needed
2. **Consistency** - All repos use same version automatically
3. **Updates** - One update propagates everywhere
4. **Less maintenance** - No local copies to track

### Scripts Use Current Working Directory

Scripts run from `~/.claude/scripts/` but operate on the current working directory (`$PWD`). This means:

```bash
# When you run this in ~/myproject:
~/.claude/scripts/commitcraft-analyze.sh

# The script runs git commands in ~/myproject
# Not in ~/.claude/scripts/
```

Commands work in any directory without knowing the script's location.

### Claude Code Environment Workaround

When scripts are invoked from Claude Code slash commands, the bash environment resets `$PWD` between calls. To handle this:

**Script pattern:**
- Scripts accept an optional first parameter for the repository directory
- Fall back to `CLAUDE_CODE_WORKING_DIR` environment variable if available
- Use current `$PWD` as final fallback
- All git commands use `git -C "$REPO_DIR"` pattern

**Slash command pattern:**
```bash
~/.claude/scripts/commitcraft-analyze.sh "$PWD"
```

This ensures scripts work correctly in both terminal and Claude Code environments.

## See Also

- Main README.md - Platform overview and usage
- docs/commitcraft-push.md - Example tool implementation
- commitcraft-install.sh - Source code for installer logic
