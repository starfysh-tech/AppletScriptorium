# Repository Guidelines

## Project Structure & Module Organization
AppletScriptorium hosts standalone automation agents as top-level directories. The active module is `Summarizer/`, containing the Python entry point (`clean-alert.py`) plus sample inputs (`alert.html`, `.eml`, `email-source.txt`) and expected outputs (`alert-cleaned.txt`, `summary.html`). Keep module assets self-contained: place new agents alongside the existing folder, and add any shared utilities to a future `shared/` package rather than cross-linking directories.

## Build, Test, and Development Commands
Use Python 3. Run the summarizer from the repo root so relative paths resolve:
- `python3 'PRO Alert Summarizer/clean-alert.py' < 'PRO Alert Summarizer/alert.html' > /tmp/alert-cleaned.txt` parses links from a Google Alert export.
- `python3 -m pip install beautifulsoup4` installs the only external dependency; pin versions in a module-specific `requirements.txt` if more packages are added.
- `python3 -m venv .venv && source .venv/bin/activate` is the recommended virtualenv workflow for contributors.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indentation and snake_case identifiers inside Python modules. Keep scripts kebab-cased (`clean-alert.py`) to mirror their command-line usage. Prefer explicit imports and pure functions so scripts can be promoted into reusable packages later. Document any non-obvious parsing logic inline with concise comments.

## Testing Guidelines
There is no automated test harness yet. Validate changes by regenerating `alert-cleaned.txt` from representative alerts and diffing against previous runs (`diff -u old.txt new.txt`). When adding summarization steps, commit sanitized fixtures into the module directory and extend manual checklists within `README.md`. Introduce pytest-based smoke tests once logic moves out of one-off scripts.

## Commit & Pull Request Guidelines
Write imperative, present-tense summaries under 60 characters (e.g., `summarizer: refine link parser`). Group related cleanups into one commit. Pull requests should describe the scenario, outline validation steps, and attach before/after artifacts (link diffs or HTML snippets). Reference issue IDs or roadmap bullets when available, and call out any new dependencies or secrets required for reviewers.

## Security & Configuration Tips
Do not commit production Google Alert content or API keys—use redacted fixtures only. Store per-agent credentials in local `.env` files ignored by git, and document any required environment variables in the module’s README before merging.
