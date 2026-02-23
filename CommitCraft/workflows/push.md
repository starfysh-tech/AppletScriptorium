# Push Workflow (Phases 1-8)

## Phases 1-3: Environment Check, Auto-Stage, and Branch Check

Execute Phases 1-3 from commit workflow (Environment Check, Auto-Stage, Branch Check).

After running `git status --porcelain`:

- **If working tree is clean** (no output from git status):
  - Check for unpushed commits: `git rev-list @{upstream}..HEAD --count 2>/dev/null || echo 0`
  - If count > 0 → skip directly to Phase 6 (Push only, no commit needed)
  - If count = 0 and no upstream branch → HARD STOP (nothing to commit or push)
  - If count = 0 and upstream exists → HARD STOP (everything is up to date)

- **If working tree has changes** (git status produced output):
  - Continue to auto-stage and commit (Phases 2-5), then push (Phase 6)
  - This applies even if there are also unpushed commits — stage, commit, then push all

Run validation:

```bash
~/.claude/skills/commitcraft/commitcraft-setup.sh --check
```

Then follow commit workflow Phases 2-3 for auto-staging and branch check.

## Phase 3: Issue Context

Run issue validation:

```bash
~/.claude/skills/commitcraft/commitcraft-issues.sh
```

Parse output. Handle per blocker table:

| STATUS | Action |
|---|---|
| `OK` | Continue, capture issue number for commit footer |
| `BLOCKED` | HARD STOP — display blocking labels, exit |
| `INCOMPLETE` | WARN — display unchecked items, auto-continue |
| `NOT_FOUND` | WARN — display "Issue #X not found", continue |
| `NO_ISSUE` | WARN — display "no linked issue found", auto-continue |
| `ERROR` | HARD STOP — display error (gh CLI missing/not authenticated), exit |

## Phase 4: AI Commit Message Generation

1. Read staged diff:

```bash
git diff --cached
```

2. Generate conventional commit message:

**Format:**
```
<type>(<scope>): <subject>

<body>

Refs #<issue>
```

**Rules:**
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`, `revert`
- Subject: imperative mood, ≤50 chars, lowercase
- Body: explain WHY not WHAT, ≤72 chars per line, can be multi-paragraph
- Scope: optional, single word (e.g., `api`, `ui`, `docs`)
- No emoji
- Footer: `Refs #<issue>` only if issue found in Phase 3
- No attribution footers (no Co-Authored-By or similar lines)

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

4. On success, capture commit hash for later use.

## Phase 6: Push to Remote

1. Check sync with remote:

```bash
git rev-list HEAD...@{upstream} --count --left-right
```

Parse output:
- `0       0` — in sync, continue
- `N       0` — ahead by N, continue
- `0       M` — behind by M, HARD STOP
- `N       M` — diverged, HARD STOP

If behind or diverged:
```
✗ Branch is behind remote
Run: git pull --rebase
```

2. Check for upstream tracking:

```bash
git rev-parse --abbrev-ref --symbolic-full-name @{upstream}
```

If no upstream, push with `-u`:

```bash
git push -u origin $(git branch --show-current)
```

Otherwise, push normally:

```bash
git push origin $(git branch --show-current)
```

3. Display push result.

## Phase 7: Issue Comment

Only if issue found in Phase 3 (STATUS = OK).

1. Capture commit hash and subject:

```bash
HASH=$(git log -1 --format=%h)
SUBJECT=$(git log -1 --format=%s)
BRANCH=$(git branch --show-current)
```

2. Post comment:

```bash
gh issue comment <NUM> --body "Commit $HASH pushed on \`$BRANCH\`: $SUBJECT"
```

3. Display confirmation.

## Phase 8: Final Report

Display summary:

```
✓ Commit: <hash> <subject>
✓ Pushed to: origin/<branch>
✓ Issue updated: #<num>

Full message:
<full commit message>
```
