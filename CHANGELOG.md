# Changelog

All notable changes to AppletScriptorium will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- **Summarizer:** add trafilatura extractor with shared quality module
- **Summarizer:** multi-model eval system with corpus caching
- **CommitCraft:** CHANGELOG automation in /commitcraft-push workflow
- **Summarizer:** improve LLM consistency with debug logging and better prompts

### Changed
- Document SwiftHAL v2.1 across repository
- **Summarizer:** add Patient Reported Outcome sample for evals
- **CommitCraft:** improve macOS compatibility and uninstall safety
- backfill CHANGELOG with missing commits
- **Summarizer:** convert tag format to emoji-only
- **Summarizer:** relax validation and remove prompt examples

### Fixed
- **Summarizer:** fix digest email UX issues (missing titles, header stats, skip single-article summary)
- **Summarizer:** fix Mail rule execution errors (missing imports, lms CLI path, model validation)
- **CommitCraft:** resolve working directory detection in Claude Code
- **Summarizer:** handle None values in digest rendering

## [4.2.0] - 2025-11-08
### Added
- **SwiftHAL:** Halstead complexity metrics analyzer with visual TUI
- **SwiftHAL:** Risk distribution histogram and architecture hotspots
- **SwiftHAL:** ArgumentParser CLI with JSON/table/summary formats
- **SwiftHAL:** Binary release (18MB) with macOS 13+ support

### Changed
- **SwiftHAL:** Swift tools version 6.2 → 5.9 for CI compatibility
- **SwiftHAL:** CI runner macos-13 → macos-latest

## [4.1.0] - 2025-10-24
### Added
- **SegmentSalmon:** M3U8/HLS video stream downloader with concurrent downloads and smart retry logic

### Changed
- Add CHANGELOG.md following Keep a Changelog standard with complete backfill of all 12 releases
- Improve release notes format with concise GitHub releases and detailed changelog
- Automate [Unreleased] section maintenance via /commitcraft-push and /commitcraft-release

## [4.0.1] - 2025-10-24
### Changed
- Restructured README for developer-first experience with complexity indicators
- Added Philosophy section explaining Larry Wall's three great virtues
- Balanced tool coverage across Summarizer, ExtensionAuditor, and CommitCraft

## [4.0.0] - 2025-10-24
### Added
- **CommitCraft:** Automated release workflow with semantic versioning and GitHub integration
- **CommitCraft:** Development workflow enhancement toolkit with AI-assisted commits and security scanning
- **ExtensionAuditor:** Chrome extension security scanner with CRXplorer compatibility

### Changed
- **CommitCraft:** Simplified architecture to 2-tier system (BREAKING: re-run `./commitcraft-install.sh`)
- Removed per-repo setup requirement - commands work in all repos after single install
- Comprehensive documentation overhaul with strategy/goals sections

### Removed
- **CommitCraft:** `commitcraft-init.sh` per-repo installer
- **CommitCraft:** `post-checkout` hook for git-based discovery

## [3.1.0] - 2025-10-22
### Added
- **Setup:** Interactive Python selection with user-friendly UI and dependency verification
- LLM-based cross-article insights for digest generation
- Bullet validation with retry for consistent summary structure

### Changed
- Improved executive summary with better decimal preservation
- Publisher metadata fallback for articles without title sources
- Increased word limit to 40 for complete findings

### Fixed
- Test suite alignment (9 test failures resolved)
- Documentation accuracy for dependencies and SMTP configuration

## [3.0.0] - 2025-10-20
### Added
- Binary content detection and URL transformation for PDFs/EPUBs
- Topic threading through complete pipeline (AppleScript to email subject)
- Emoji indicators for Tactical Win tags
- LM Studio error diagnostics with prompt size logging

### Changed
- **Summarizer:** Binary content now transforms to HTML (BREAKING: .env uses SMTP_* variables)
- Mail rule simplified to subject-only filtering (removed From requirement)
- Tag normalization with case-insensitive regex
- Ollama health detection and auto-recovery after timeouts
- Replaced UI automation with direct SMTP email delivery (BREAKING: requires SMTP credentials)

### Removed
- Debug files and .env.example to prevent accidental commits

## [2.3.2] - 2025-10-15
### Fixed
- Minor improvements

## [2.3.1] - 2025-10-15
### Changed
- Audit and correct documentation for accuracy
- Fix npm package name references
- Update workflow diagram to reflect current architecture
- Remove obsolete test scripts

## [2.3.0] - 2025-10-15
### Added
- Jina API key acquisition instructions via browserling.com

### Changed
- **Fetcher:** Replace Playwright with url-to-md/Jina fallback (BREAKING: removes Crawlee dependency)
- Implement dual-cache architecture for HTML/Markdown
- Add Markdown cleanup and validation helpers

### Fixed
- **Mail rule:** Dynamic subject line extraction
- Window verification error after successful email send

## [2.2.0] - 2025-10-14
### Added
- User workflow guide with visual diagram
- Workflow diagram (PNG and Mermaid source)
- SUMMARY_PROMPT_TEMPLATE constant in config.py

### Changed
- Reorganized documentation into `docs/` directory
- Made summary prompt topic-agnostic
- Simplified _build_prompt() function

## [2.1.0] - 2025-10-14
### Changed
- Streamlined documentation to eliminate duplication (11% reduction)
- Consolidated MAIL_RULE_SETUP.md into SETUP.md
- Focused README on landing page essentials
- Created dedicated TROUBLESHOOTING.md
- Switched default model from granite4:tiny-h to qwen3:latest

### Removed
- MAIL_RULE_SETUP.md (merged into other docs)

## [2.0.1] - 2025-10-14
### Fixed
- Reverted UV migration - Mail automation requires pip's --user flag
- UV compatibility issues with system Python
- Permission errors with UV's --system flag

## [2.0.0] - 2025-10-14
### Added
- UV package manager support for faster installs (later reverted in v2.0.1)

### Changed
- Removed all backward compatibility for PRO_ALERT_* variables (BREAKING: must use ALERT_* variables)
- Improved validate.sh with progress indicators

### Fixed
- validate.sh now continues on failures (removed set -e)

## [1.0.0] - 2025-10-14
### Added
- Initial release of Google Alert Intelligence framework
- Automated setup with install.sh
- Interactive Mail rule configuration
- Validation script with 10 comprehensive checks
- Template system for Mail rule scripts
- Centralized configuration in config.py
- Article fetching with Crawlee/Playwright for bot-protected sites
- Content extraction with readability-lxml
- Ollama integration for LLM-based summarization
- HTML and text digest rendering
- SMTP email delivery
- Scheduled execution via cron
- Comprehensive documentation (README, SETUP, TROUBLESHOOTING, CLAUDE, AGENTS)
- Pytest test suite with 21 tests
- Fixture-based testing with sample emails
- Topic-agnostic framework (works with any Google Alert)

### Changed
- Rebranded from "PRO Alert Summarizer" to "Google Alert Intelligence"
- Environment variables: PRO_ALERT_* → ALERT_* (with backward compatibility)
- Script names: run_pro_alert.sh → run_alert.sh
- AppleScript: process-pro-alert.scpt → process-alert.scpt
- Config file: ~/.pro-alert-env → ~/.alert-env

[unreleased]: https://github.com/starfysh-tech/AppletScriptorium/compare/v4.2.0...HEAD
[4.2.0]: https://github.com/starfysh-tech/AppletScriptorium/releases/tag/v4.2.0
[4.1.0]: https://github.com/starfysh-tech/AppletScriptorium/compare/v4.0.1...v4.1.0
[4.0.1]: https://github.com/starfysh-tech/AppletScriptorium/compare/v4.0.0...v4.0.1
[4.0.0]: https://github.com/starfysh-tech/AppletScriptorium/compare/v3.1.0...v4.0.0
[3.1.0]: https://github.com/starfysh-tech/AppletScriptorium/compare/v3.0.0...v3.1.0
[3.0.0]: https://github.com/starfysh-tech/AppletScriptorium/compare/v2.3.2...v3.0.0
[2.3.2]: https://github.com/starfysh-tech/AppletScriptorium/compare/v2.3.1...v2.3.2
[2.3.1]: https://github.com/starfysh-tech/AppletScriptorium/compare/v2.3.0...v2.3.1
[2.3.0]: https://github.com/starfysh-tech/AppletScriptorium/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/starfysh-tech/AppletScriptorium/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/starfysh-tech/AppletScriptorium/compare/v2.0.1...v2.1.0
[2.0.1]: https://github.com/starfysh-tech/AppletScriptorium/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/starfysh-tech/AppletScriptorium/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/starfysh-tech/AppletScriptorium/releases/tag/v1.0.0
