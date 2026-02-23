# Commit Workflow (Phases 1-6)

## Phase 1: Environment Check

Run validation:

```bash
~/.claude/skills/commitcraft/commitcraft-setup.sh --check
```

Parse output. If critical items missing (commitlint, gitleaks, precommit_hooks), display warning:

```
⚠ Tooling incomplete - some checks will be skipped
Run /commitcraft setup for full configuration
```

Continue regardless of status.

## Phase 2: Stage Changes

1. Run git status and diff:

```bash
git status --porcelain
git diff --stat
```

2. Check for blockers:

| Condition | Action |
|---|---|
| Merge conflicts (git status shows `UU`, `AA`, `DD`) | HARD STOP — show conflicts, exit |
| Detached HEAD | HARD STOP — show current state, exit |

3. Auto-stage all changes:

- Parse `git status --porcelain` output
- Stage each modified/untracked file individually: `git add <file>` (never use `git add -A`)
- If nothing to stage after auto-staging, HARD STOP — "no changes to commit", exit

4. Run final staged diff:

```bash
git diff --cached --stat
```

Display summary. If >1000 lines changed, warn about large diff.

## Phase 3: Branch Check

After staging, before generating commit message:

1. Get current branch:

```bash
git branch --show-current
```

2. If on `main` or `master`:

   - Proceed to Phase 4 to generate commit message
   - After message generated, query for open issues:

   ```bash
   gh issue list --state open --limit 3 --json number,title
   ```

   - **Present issue selection via AskUserQuestion:**
     - Show up to 3 recent open issues + "No issue" option
     - Header: `"Issue"`
     - Option format: `#<num>: <title>` (truncate title if needed for readability)
     - "Other" is automatically available (user can type any issue number)

   - **Fallback handling** (do NOT prompt):
     - If `gh` not installed/authenticated → skip query, use no issue number
     - If 0 issues returned → skip prompt, use no issue number

   - **Derive branch name** from commit type/scope/subject:
     - With issue: `<type>/<slugified-subject>-<issue_num>` (e.g., `feat/add-interactive-ship-script-305`)
     - No issue: `<type>/<slugified-subject>` (e.g., `feat/add-interactive-ship-script`)

   - Create and switch: `git checkout -b <branch-name>`
   - Note: staged files automatically carry over to new branch
   - Skip to Phase 5 (commit already has message)

3. If already on a feature branch:

   - Continue to Phase 4 normally

## Phase 4: AI Commit Message Generation

This is the core AI value.

1. Read staged diff:

```bash
git diff --cached
```

2. Generate conventional commit message:

**Format:**
```
<type>(<scope>): <subject>

<body>
```

**Rules:**
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`, `revert`
- Subject: imperative mood, ≤50 chars, lowercase
- Body: explain WHY not WHAT, ≤72 chars per line, can be multi-paragraph
- Scope: optional, single word (e.g., `api`, `ui`, `docs`)
- No emoji
- No attribution footers (no Co-Authored-By or similar lines)

**Subject examples:**
- `feat(api): add user authentication endpoint`
- `fix(ui): correct button alignment in modal`
- `docs: update installation instructions`
- `refactor(core): simplify error handling logic`

**Body guidelines:**
- Focus on motivation and context
- Reference related issues/PRs if relevant
- Explain non-obvious decisions
- Skip if change is self-evident

## Phase 5: Commit

1. Commit with HEREDOC (preserves formatting):

```bash
git commit -m "$(cat <<'EOF'
<generated message here>
EOF
)"
```

2. Pre-commit hooks run automatically (gitleaks, commitlint, linters).

3. Handle hook failures:

| Failure Type | Action |
|---|---|
| gitleaks detects secrets | HARD STOP — show findings, never suggest `--no-verify`, exit |
| commitlint format error | HARD STOP — show error, suggest fix, never suggest `--no-verify`, exit |
| Auto-fixable (prettier, eslint --fix) | SOFT BLOCK — show fixed files, re-stage, retry commit |
| Test failures | HARD STOP — show failures, exit |

**Never use `--no-verify` or any hook-skipping flags.**

4. On success, capture commit hash and display:

```bash
git log -1 --oneline
```

Output:
```
✓ Committed: <hash> <subject>
Branch: <branch-name>
```

## Phase 6: End

Commit workflow ends here.
