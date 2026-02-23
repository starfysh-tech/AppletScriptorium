# PR Creation Workflow

## Phase 0: Branch & Commit Gate

Check working state before PR creation:

```bash
BRANCH=$(git branch --show-current)
git status --porcelain
```

**If on `main` or `master`:**

1. If uncommitted changes exist:
   - Follow `workflows/commit.md` Phases 1-5 (stage, generate message, create branch, commit)
   - After commit completes on the new branch, continue to Phase 1
2. If no uncommitted changes:
   - Stop: "No changes to create a PR from. Make changes first, then run `/commitcraft pr`."

**If on a feature branch:**

Continue to Phase 1.

## Phase 1: Check for Existing PR

Check if a PR already exists for the current branch:

```bash
gh pr view --json state,url 2>/dev/null
```

**Handling:**
- If PR exists → Display URL, ask if user wants to update description or exit
- If no PR found → Continue to Phase 2

## Phase 2: Gather Context

Collect branch and commit information:

```bash
BRANCH=$(git branch --show-current)
git log main..HEAD --oneline
git diff main...HEAD --stat
```

Parse commits to understand:
- What changed (files, functions, features)
- Why it changed (commit messages)
- Scope of changes (additions/deletions)

## Phase 3: Generate PR Description

Create PR description following this format:

```markdown
## Summary
[One paragraph overview of what this PR does and why]

## Changes
- **Component/Area:** Description of change
- **Component/Area:** Description of change

## Test plan
- [ ] Verification step 1
- [ ] Verification step 2
- [ ] Verification step 3

---
Claude Code (<model>)
```

**Style Guidelines:**
- Summary: 1-2 paragraphs, explain the "why" not just the "what"
- Changes: Bold prefix for component/area, group related changes
- Test plan: Checkbox format `- [ ]`, actionable verification steps
- Keep concise and scannable

## Phase 4: Determine PR Title

Generate conventional commit-style title from commits:

```
<type>(<scope>): <summary>
```

**Rules:**
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`
- Summary: imperative mood, ≤70 chars, lowercase
- Scope: optional, single word from commits

## Phase 5: Check for Linked Issue

Look for issue references in commits:

```bash
git log main..HEAD --format=%B | grep -E "(Refs|Closes|Fixes) #[0-9]+"
```

If issue found, prepare to link in PR body (add `Closes #<num>` to Summary if appropriate).

## Phase 6: Create PR

Ask user via `AskUserQuestion`:
- "Create pull request?" → Yes / Yes (draft) / Skip

If user chooses to create:

```bash
gh pr create --title "<type>(<scope>): <summary>" --body "$(cat <<'EOF'
## Summary
[Generated summary with issue reference if found]

## Changes
- **Component:** Description

## Test plan
- [ ] Step 1

---
Claude Code (<model>)
EOF
)"
```

Add flags:
- `--draft` if user selected draft
- `--web` to open in browser after creation

Capture PR URL from output.

## Phase 7: Final Report

Display result:

```
✓ PR created: <url>
✓ Branch: <branch>
✓ Commits: N commits since main
```

Or if skipped:

```
PR creation skipped
```
