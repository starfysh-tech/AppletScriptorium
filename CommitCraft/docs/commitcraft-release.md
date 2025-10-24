# CommitCraft Automated Release Tool (/commitcraft-release)

## Overview

The `/commitcraft-release` command provides automated semantic versioning and GitHub release creation with intelligent version bump detection and auto-generated release notes. It analyzes your conventional commits, determines the appropriate version bump, and publishes a GitHub release—all automatically unless there's a blocker.

## What It Provides

- **Version bump detection** - Analyzes commits to determine major/minor/patch
- **Conventional commit parsing** - Categorizes changes by type (breaking/feat/fix/docs)
- **CHANGELOG.md maintenance** - Updates Keep a Changelog formatted version history
- **Concise release notes** - User-focused GitHub release summaries
- **Git tag creation** - Creates and pushes semver tags
- **GitHub release publishing** - Uses `gh` CLI to create releases
- **Clean tree validation** - Ensures no uncommitted changes before releasing

## Command Usage

### Basic Workflow

When you run `/commitcraft-release` in Claude Code, the following happens automatically:

1. **Analysis** - Runs `~/.claude/scripts/commitcraft-release-analyze.sh` for version analysis
2. **Blocker check** - Stops if uncommitted changes, missing gh CLI, or no commits since last release
3. **Version detection** - Auto-detects bump type from conventional commits
4. **CHANGELOG.md update** - Moves [Unreleased] → new version section, validates against git commits
5. **GitHub release notes** - Generates concise user-focused summary from CHANGELOG content
6. **Tag creation** - Creates annotated git tag with new version
7. **Push tag** - Pushes tag to origin
8. **Commit CHANGELOG** - Commits and pushes updated CHANGELOG.md
9. **GitHub release** - Creates release via `gh` CLI with concise notes

**Fully automated unless blocked.** No user interaction needed unless there's a problem.

### Example Usage

**Scenario:** You've committed several features and fixes since the last release.

```bash
/commitcraft-release
```

**You see analysis output:**

```
=== CommitCraft Release Analysis ===

✓ Working tree is clean
✓ GitHub CLI authenticated

Current version: v3.1.0
Commits since release: 8

Commit breakdown:
  🚨 Breaking changes: 0
  ✨ Features: 3
  🐛 Bug fixes: 2
  📚 Documentation: 2
  Other: 1

Suggested bump: minor
New version: v3.2.0

Recent commits:
79612aa ✨ feat(setup): add interactive Python selection
f0ac055 🧪 test: fix test suite for code changes
352ac3f 📚 docs(claude): remove redundant SMTP config notes
84f5e05 docs: align documentation with code implementation
56da603 ✨ feat(digest): improve formatting and add insights
...

✓ Ready to create release
```

Claude then:
1. Moves [Unreleased] content to v3.2.0 section in CHANGELOG.md
2. Validates against git commits (safety net)
3. Generates concise GitHub release notes from CHANGELOG
4. Creates tag `v3.2.0`
5. Pushes tag to origin
6. Commits and pushes CHANGELOG.md
7. Creates GitHub release
8. Reports success with release URL

## Version Bump Rules

The command automatically detects the version bump type based on conventional commits:

### Major Version (Breaking Changes)

**Trigger:** Any commit contains `BREAKING CHANGE` in the body or footer

**Example commits:**
```
feat(api): redesign authentication flow

BREAKING CHANGE: Auth endpoints now require OAuth2 tokens
```

**Result:** v2.0.0 → v3.0.0

### Minor Version (Features)

**Trigger:** Commits with `feat:` type (and no breaking changes)

**Example commits:**
```
feat(ui): add dark mode toggle
feat(search): implement fuzzy matching
```

**Result:** v2.0.0 → v2.1.0

### Patch Version (Bug Fixes)

**Trigger:** Commits with `fix:` type (and no features or breaking changes)

**Example commits:**
```
fix(auth): prevent token expiration race condition
fix(ui): correct button alignment on mobile
```

**Result:** v2.0.0 → v2.0.1

### Other Commit Types

**Trigger:** Only `docs:`, `test:`, `chore:`, `refactor:`, etc. commits

**Default:** Patch version bump

**Result:** v2.0.0 → v2.0.1

## Release Documentation Format

CommitCraft generates two complementary release artifacts:

### 1. CHANGELOG.md (Detailed)

Maintained in the repository root following the [Keep a Changelog](https://keepachangelog.com) standard.

**Purpose:** Comprehensive version history for developers and contributors.

**Format:**
```markdown
## [4.1.0] - 2025-10-24
### Added
- **SegmentSalmon:** M3U8/HLS video stream downloader
- Automated release workflow with semantic versioning

### Changed
- **CommitCraft:** Simplified architecture (BREAKING: re-run installer)
- Improved README structure with complexity indicators

### Fixed
- Test suite alignment after content-type changes

[4.1.0]: https://github.com/owner/repo/compare/v4.0.1...v4.1.0
```

**Section order:**
1. **Added** - New features (`feat:` commits)
2. **Changed** - Modifications to existing functionality (`refactor:`, breaking changes)
3. **Deprecated** - Soon-to-be removed features
4. **Removed** - Deleted features
5. **Fixed** - Bug fixes (`fix:` commits)
6. **Security** - Security patches

**Omitted:** `test:`, `chore:`, `ci:` commits (internal changes)

### 2. GitHub Release Notes (Concise)

User-focused summary published on GitHub Releases page.

**Purpose:** Quick overview for users to understand what changed and why they should upgrade.

**Format:**
```markdown
This release adds M3U8 video downloading and improves documentation.

## What's New

- M3U8/HLS video stream downloader with parallel downloads
- Developer-first README with complexity indicators
- Automated release workflow

See [CHANGELOG.md](CHANGELOG.md) for complete details.

**Full Changelog**: https://github.com/owner/repo/compare/v4.0.1...v4.1.0
```

**Rules:**
- Brief opening summary (2-3 sentences)
- 2-4 high-level theme bullets (not individual commits)
- Link to CHANGELOG.md for details
- Under 30 lines total
- User benefits, not implementation details

### Commit Formatting (Both Formats)

**Subject line processing:**
- Emojis removed
- Type prefix removed: `feat(api): add endpoint` → `Add endpoint`
- Scope preserved as bold: `feat(api): add endpoint` → `**API:** Add endpoint`
- Breaking changes get suffix: `(BREAKING: re-run installer)`

## The commitcraft-release-analyze.sh Script

### What It Does

Comprehensive release readiness analysis including:

1. **GitHub CLI Validation**
   - Checks if `gh` CLI is installed
   - Verifies authentication status
   - Blocks if missing or not authenticated

2. **Working Tree Validation**
   - Checks for uncommitted changes
   - Blocks if working tree is dirty
   - Ensures clean state before release

3. **Tag Parsing**
   - Finds latest semver tag
   - Parses version (vMAJOR.MINOR.PATCH format)
   - Handles first release (no tags)

4. **Commit Analysis**
   - Gets commits since last tag
   - Categorizes by type (breaking/feat/fix/docs/other)
   - Counts commits per category

5. **Version Calculation**
   - Applies semver rules based on commit types
   - Suggests new version
   - Handles version resets (major bumps reset minor/patch)

6. **Context Display**
   - Shows commit breakdown with color coding
   - Lists recent commits for review
   - Confirms release readiness

### Running Manually

You can run the analysis script directly to check release status:

```bash
# Via full path
~/.claude/scripts/commitcraft-release-analyze.sh
```

**Example output:**

```
=== CommitCraft Release Analysis ===

✓ Working tree is clean
✓ GitHub CLI authenticated

Current version: v3.1.0
Commits since release: 5

Commit breakdown:
  ✨ Features: 2
  🐛 Bug fixes: 1
  📚 Documentation: 2

Suggested bump: minor
New version: v3.2.0

Recent commits:
abc1234 ✨ feat(api): add rate limiting
def5678 🐛 fix(auth): handle expired tokens
ghi9012 📚 docs: update API documentation
jkl3456 📚 docs: add migration guide
mno7890 ✨ feat(ui): add loading states

✓ Ready to create release
```

**Use cases:**
- Check if release is ready before running `/commitcraft-release`
- Preview what the next version will be
- Review commit categorization
- Verify GitHub CLI setup

## Blockers

The command stops only for these issues:

### 🛑 GitHub CLI Not Found

**Message:**
```
✗ GitHub CLI (gh) not found

Install: brew install gh
Then authenticate: gh auth login
```

**Resolution:**
```bash
# Install gh CLI
brew install gh

# Authenticate
gh auth login
```

### 🛑 GitHub CLI Not Authenticated

**Message:**
```
✗ GitHub CLI not authenticated

Run: gh auth login
```

**Resolution:**
```bash
gh auth login
```

Follow the prompts to authenticate with your GitHub account.

### 🛑 Uncommitted Changes

**Message:**
```
✗ Working tree has uncommitted changes

Commit or stash changes before creating a release
```

**Resolution:**
```bash
# Option 1: Commit changes
git add .
git commit -m "fix: final changes before release"

# Option 2: Stash changes
git stash

# Then run /commitcraft-release again
```

### 🛑 No Commits Since Last Release

**Message:**
```
⚠️  No commits since v3.1.0

Nothing to release
```

**Resolution:** Make commits, then try again. No release needed if nothing has changed.

### ⚠️  No Existing Tags (First Release)

**Message:**
```
⚠️  No existing tags found

Suggested first version: v1.0.0
Commits in repository: 42
```

**Not a blocker** - the command will create the first release as `v1.0.0`.

## Integration with Workflow

### Typical Release Workflow

1. **Develop features** - Make commits following conventional format
2. **Ensure commits pushed** - Run `/commitcraft-push` to push changes
3. **Create release** - Run `/commitcraft-release` to publish

**Example:**
```bash
# After implementing features
/commitcraft-push

# When ready to release
/commitcraft-release
```

### Conventional Commit Format

For best results, follow conventional commit format:

**Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat:` - New feature (minor bump)
- `fix:` - Bug fix (patch bump)
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring
- `chore:` - Build/tooling changes

**Breaking changes:**
```
feat(api): redesign endpoints

BREAKING CHANGE: All API endpoints now require authentication
```

**With scope:**
```
feat(auth): add OAuth2 support
fix(ui): correct button alignment
```

### Release Frequency

**Recommendations:**

- **Features accumulated** - Release when 3-5 features merged
- **Critical fixes** - Release immediately for security/bug fixes
- **Documentation updates** - Batch with other changes
- **Breaking changes** - Release separately with clear migration guide

## Troubleshooting

### Release Notes Missing Commits

**Problem:** Some commits don't appear in release notes

**Causes:**
1. Commits don't follow conventional format
2. Commits are categorized under "Other Changes"

**Solutions:**
- Use conventional commit format (`feat:`, `fix:`, etc.)
- Check "Other Changes" section for miscategorized commits

### Wrong Version Bump

**Problem:** Expected minor bump but got patch (or vice versa)

**Causes:**
1. No `feat:` commits (only fixes → patch)
2. Didn't include `BREAKING CHANGE` in body

**Solutions:**
- Verify commit types: `git log v3.1.0..HEAD --oneline`
- Use `feat:` for features, add `BREAKING CHANGE` for major bumps
- Check analysis output before release

### GitHub Release Not Created

**Problem:** Tag created but no GitHub release

**Causes:**
1. Not authenticated with `gh` CLI
2. No push access to repository
3. Network error during release creation

**Solutions:**
```bash
# Check authentication
gh auth status

# Re-authenticate if needed
gh auth login

# Create release manually from tag
gh release create v3.2.0 --generate-notes
```

### Tag Already Exists

**Problem:** Cannot create tag because it already exists

**Cause:** Tag was created in a previous run that failed partway through

**Solutions:**
```bash
# Delete local tag
git tag -d v3.2.0

# Delete remote tag (if pushed)
git push origin :refs/tags/v3.2.0

# Run /commitcraft-release again
```

## Advanced Usage

### Preview Release Notes

Want to see what the release notes will look like before creating?

```bash
# Run analysis script
~/.claude/scripts/commitcraft-release-analyze.sh

# Then check commits manually
git log v3.1.0..HEAD --format="%s"
```

### Manual Release (Without Command)

If you need to create a release manually:

```bash
# Create tag
git tag -a v3.2.0 -m "v3.2.0"

# Push tag
git push origin v3.2.0

# Create GitHub release
gh release create v3.2.0 --title "v3.2.0 - Feature Summary" --notes "Release notes here"
```

### Custom Release Notes

The command generates notes automatically, but you can edit them in GitHub:

1. Run `/commitcraft-release` to create release
2. Visit release URL in browser
3. Click "Edit release"
4. Modify notes as needed
5. Save changes

## Best Practices

### Before Creating Release

1. **Review changes** - Run analysis script to preview
2. **Clean working tree** - Commit or stash all changes
3. **Pull latest** - Ensure you have latest commits from remote
4. **Check CI** - Verify tests pass before releasing

### Commit Message Quality

**Good examples:**
```
feat(auth): add two-factor authentication support
fix(api): handle rate limit errors gracefully
docs(readme): update installation instructions
```

**Bad examples:**
```
update stuff
wip
fixes
```

### Version Strategy

- **Major (v2.0.0 → v3.0.0)** - Breaking changes, major features
- **Minor (v2.0.0 → v2.1.0)** - New features, no breaking changes
- **Patch (v2.0.0 → v2.0.1)** - Bug fixes, documentation

### Release Timing

- **Don't rush** - Batch related changes together
- **Don't delay** - Release security fixes immediately
- **Communicate** - Add migration notes for breaking changes

## See Also

- [CommitCraft README](../README.md) - Platform overview
- [Conventional Commits](https://www.conventionalcommits.org/) - Commit format specification
- [Semantic Versioning](https://semver.org/) - Version numbering rules
- [GitHub CLI Documentation](https://cli.github.com/manual/) - `gh` command reference
