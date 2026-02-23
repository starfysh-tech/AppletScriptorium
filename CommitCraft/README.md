# CommitCraft v5

AI-powered git workflow toolkit for Claude Code. Handles conventional commits, issue validation, PR creation, and release guidance — through a single skill with 6 workflows.

## Quick Start

```bash
# One-time global install
cd CommitCraft && ./commitcraft-install.sh

# Invoke in any git repo via Claude Code
/commitcraft commit    # AI-generated conventional commit
/commitcraft push      # Commit + push with issue tracking
/commitcraft pr        # Create PR with AI-generated description
/commitcraft release   # Semantic version bump and release guidance
/commitcraft setup     # Interactive tooling configuration
/commitcraft check     # Validate current configuration
```

## Workflows

| Workflow | Description |
|---|---|
| `commit` | Stages files individually, generates conventional commit message, handles pre-commit hooks |
| `push` | Full commit + push with issue validation, branch tracking, and post-push issue comments |
| `pr` | Creates PR with AI-generated description, issue linking, draft support |
| `release` | Guides semantic versioning via release-please (if configured) or manual tag workflow |
| `setup` | Interactive 7-component tooling setup (commitlint, gitleaks, pre-commit, signing, release-please, CI, branch protection) |
| `check` | Validates installed tooling and reports configuration status |

## Skill Architecture

CommitCraft is implemented as a Claude Code skill:

```
~/.claude/skills/commitcraft/
├── SKILL.md                    # Skill definition — routes /commitcraft <arg> to workflow
├── commitcraft-setup.sh        # Interactive tooling setup + --check mode
├── commitcraft-issues.sh       # Branch-based GitHub issue validation
├── commitcraft-release-analyze.sh  # Semantic version analysis (fallback release)
├── workflows/
│   ├── commit.md               # Commit workflow (phases 1–6)
│   ├── push.md                 # Push workflow (phases 1–8)
│   ├── pr.md                   # PR creation workflow (phases 0–7)
│   ├── release.md              # Release workflow (steps 1–2)
│   ├── setup.md                # Setup workflow
│   └── check.md                # Check workflow
└── templates/
    ├── commitlint.config.js    # Conventional commit rules
    ├── .commitlintrc.yml       # commitlint config
    ├── .gitleaks.toml          # Secret scanning rules
    ├── .pre-commit-config.yaml # Pre-commit hook config
    ├── commitlint-ci.yml       # GitHub Actions: commit linting
    ├── release-please.yml      # GitHub Actions: release-please
    └── release-please-config.json  # release-please manifest
```

`SKILL.md` routes `/commitcraft <argument>` by reading the corresponding `workflows/<argument>.md` file. The skill runs in a fork context using the Haiku model, keeping the main conversation context clean.

## Behavioral Conventions

- **No `git add -A`** — each file is staged individually (`git add <file>`)
- **No emoji prefixes** in commit messages
- **No attribution footers** (no Co-Authored-By or similar)
- **Never `--no-verify`** — hook failures are hard stops, not bypasses
- **Branch from main** — commit workflow auto-creates feature branches when on main

## Supporting Scripts

### `commitcraft-setup.sh`
Interactive setup for 7 tooling components. Installs and configures them per-repository.

```bash
# Full interactive setup
~/.claude/skills/commitcraft/commitcraft-setup.sh

# Check-only mode (used by workflows)
~/.claude/skills/commitcraft/commitcraft-setup.sh --check

# Configure specific section
~/.claude/skills/commitcraft/commitcraft-setup.sh --section signing
```

### `commitcraft-issues.sh`
Validates current branch against GitHub issues. Reads issue number from branch name (e.g., `feat/my-feature-305` → issue #305), checks labels and completion status.

```bash
~/.claude/skills/commitcraft/commitcraft-issues.sh
# Outputs: OK | BLOCKED | INCOMPLETE | NOT_FOUND | NO_ISSUE | ERROR
```

### `commitcraft-release-analyze.sh`
Analyzes git log for conventional commits to determine semantic version bump. Used as fallback when release-please is not configured.

```bash
~/.claude/skills/commitcraft/commitcraft-release-analyze.sh
```

## Installation Details

```bash
cd CommitCraft && ./commitcraft-install.sh
```

The installer:
- Detects state: not installed, legacy v4.x found, updates available, or up to date
- Cleans up legacy v4.x files (`~/.claude/scripts/commitcraft-*`, `~/.claude/commands/commitcraft-*`) automatically
- Installs 17 files to `~/.claude/skills/commitcraft/` preserving subdirectory structure
- Uses MD5 hashing for accurate change detection (not timestamps)
- Grouped TUI display: SKILL.md + scripts (3) + workflows (6) + templates (7)
- File-by-file uninstall (no `rm -rf`)

## Migration from v4.x

| v4.x | v5.0 |
|---|---|
| `/commitcraft-push` | `/commitcraft push` |
| `/commitcraft-release` | `/commitcraft release` |
| `~/.claude/scripts/commitcraft-analyze.sh` | `~/.claude/skills/commitcraft/commitcraft-setup.sh --check` |
| `~/.claude/commands/commitcraft-push.md` | `~/.claude/skills/commitcraft/workflows/push.md` |
| `~/.claude/commands/commitcraft-release.md` | `~/.claude/skills/commitcraft/workflows/release.md` |
| Install: `~/.claude/scripts/` + `commands/` | Install: `~/.claude/skills/commitcraft/` |

**To migrate:** Re-run `./commitcraft-install.sh`. The installer detects and removes old files automatically.

## Troubleshooting

**Skill not found after install**
- Verify: `ls ~/.claude/skills/commitcraft/SKILL.md`
- If missing, re-run installer

**`/commitcraft <workflow>` does nothing**
- The skill routes via `$ARGUMENTS` — use lowercase: `commit`, `push`, `pr`, `release`, `setup`, `check`
- If argument is misspelled, skill falls back to `commit` workflow

**`commitcraft-setup.sh --check` fails**
- Some tools are optional (commitlint, gitleaks, pre-commit)
- Workflows continue even without full tooling — missing checks are skipped

**Legacy files still present**
- Run installer — it detects and removes them
- Or manually: `rm ~/.claude/scripts/commitcraft-* ~/.claude/commands/commitcraft-*`

**`gh` not authenticated**
- Issue validation and PR creation require `gh auth login`
- Workflows degrade gracefully: issue steps are skipped, PR creation fails with clear error
