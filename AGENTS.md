# Repository Guidelines

## Agent Role & Scope
AppletScriptorium agents are expected to operate as macOS automation specialists fluent in AppleScript/osascript, shell (bash/zsh), and Python helpers. Build the simplest thing that works on the maintainer’s local Mac—avoid speculative abstractions or premature generalization. Still add pragmatic logging, error handling, idempotency, and locks where they materially improve reliability. Ask clarifying questions only when requirements are ambiguous.

## Collaboration Workflow
The maintainer will issue focused tasks sequentially (e.g., “write AppleScript to fetch message source,” “add locking wrapper”). For each task deliver:
- Production-ready scripts or modules placed under the appropriate agent directory.
- Inline comments explaining non-obvious logic and integration points.
- Tests or usage examples (CLI invocation, mocked runs) demonstrating expected behavior.
Document assumptions in the PRD or README so future tasks start with full context, and call out when a deliberately simple approach was chosen.

## Project Structure & Module Organization
Each automation agent lives at the repository root (current module: `Summarizer/`). Keep fixtures, scripts, and docs self-contained within the agent directory. Shared utilities will eventually reside in `shared/`, but avoid cross-linking until that package exists. Preserve sample artifacts under `Summarizer/Samples/` (committed `google-alert-patient-reported-outcome-2025-10-06.*` files) because they anchor regression tests.

## Build, Test, and Development Commands
Use Python 3.11+.
- `osascript Summarizer/fetch-alert-source.applescript Summarizer/Samples/google-alert-patient-reported-outcome-2025-10-06.eml` refreshes the raw alert fixture in-place.
- `Summarizer/refresh-fixtures.py` rebuilds the decoded HTML and expected link list.
- `python3 'Summarizer/clean-alert.py'` still prints anchor text/URLs from the fixture for quick spot checks.
- `python3 -m venv .venv && source .venv/bin/activate` creates an isolated environment.
- `python3 -m pip install -r Summarizer/requirements.txt` installs declared Python dependencies.
Keep shell wrappers executable (`chmod +x`) and provide example invocations in README updates.

## Coding Style & Naming Conventions
Follow PEP 8 (4-space indents) and snake_case for Python; kebab-case script filenames (e.g., `fetch-alert.scpt`). AppleScript files should include header comments describing trigger conditions. Prefer pure functions and dependency injection to ease unit testing and future reuse.

## Testing & Validation Guidelines
Until automated tests are wired, rely on fixture-driven diffs: rebuild `google-alert-patient-reported-outcome-2025-10-06-links.tsv` with `refresh-fixtures.py` and compare against the committed version (`diff -u`). When adding new modules, include pytest smoke tests, AppleScript usage notes, or shell dry-run flags. Capture expected JSON/HTML digests as golden files to guard regressions.

## Commit & Pull Request Expectations
Write imperative commit subjects under ~60 chars (e.g., `summarizer: add link parser`). Each PR should summarize the scenario, list validation steps, and attach relevant artifacts (diffs, HTML snippets, logs). Reference issues/roadmap bullets and note new dependencies or secret requirements for reviewers.

## Security & Configuration Tips
Never commit live Google Alert content, API keys, or Mail credentials. Use redacted fixtures and `.env` files ignored by git. Document required env vars and configuration updates in the README before merging.
