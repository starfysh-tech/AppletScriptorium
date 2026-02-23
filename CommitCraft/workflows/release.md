# Release Workflow

## Step 1: Check for release-please

Run setup check:

```bash
~/.claude/skills/commitcraft/commitcraft-setup.sh --check
```

Parse output. Check `release_please` status.

## Step 2a: If release-please CONFIGURED

1. Check for open release PR:

```bash
gh pr list --label "autorelease: pending" --json number,title,url
```

2. If PR exists:

Display PR details. Offer via `AskUserQuestion`:
- Review PR
- Enhance release notes with AI
- Merge PR (guide user, don't auto-merge)

3. If no PR exists:

Explain:
```
release-please creates release PRs automatically when conventional commits are pushed to main.

To trigger:
1. Merge feature branch to main
2. Wait for release-please action
3. Review generated release PR

Current branch: <branch>
Run /commitcraft push to merge changes
```

## Step 2b: If release-please NOT CONFIGURED

Run fallback release analyze:

```bash
~/.claude/skills/commitcraft/commitcraft-release-analyze.sh
```

Parse output between `RELEASE_ANALYZE_START` and `RELEASE_ANALYZE_END`.

Extract:
- `CURRENT_VERSION`
- `NEW_VERSION`
- `BUMP_TYPE`
- `COMMIT_COUNT`

Display analysis. Guide user through manual release:

1. Create tag: `git tag <NEW_VERSION>`
2. Push tag: `git push origin <NEW_VERSION>`
3. Create release: `gh release create <NEW_VERSION> --generate-notes`

**Recommendation:**
```
⚠ Manual release workflow

For automated releases with proper changelog management:
Run /commitcraft setup
```
