# Changelog

All notable changes to AppletScriptorium will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [4.0.1] - 2025-10-24
### Changed
- Restructured README for developer-first experience with complexity indicators
- Added Philosophy section explaining Larry Wall's three great virtues
- Balanced tool coverage across Summarizer, ExtensionAuditor, and CommitCraft

## [4.0.0] - 2025-10-24
### Added
- **CommitCraft:** Automated release workflow with semantic versioning
- **CommitCraft:** Development workflow enhancement toolkit with AI-assisted commits
- **ExtensionAuditor:** Chrome extension security scanner

### Changed
- **CommitCraft:** Simplified architecture to 2-tier system (BREAKING: re-run `./commitcraft-install.sh`)
- Removed per-repo setup requirement - commands work in all repos after single install
- Comprehensive documentation overhaul with strategy/goals sections

### Removed
- **CommitCraft:** `commitcraft-init.sh` - per-repo installer no longer needed
- **CommitCraft:** `post-checkout` hook - git hook-based discovery removed

## [3.1.0] - 2025-10-22
### Added
- Interactive Python selection with user-friendly UI and dependency verification
- LLM-based cross-article insights for digest generation
- Bullet validation with retry for consistent summary structure

### Changed
- Improved executive summary with better decimal preservation
- Publisher metadata fallback for articles without title sources

### Fixed
- Test suite alignment (9 test failures resolved)
- Documentation accuracy for dependencies and SMTP configuration

## [3.0.0] - 2025-10-20
### Added
- Binary content support for article fetching
- Topic threading for multi-topic Google Alerts

### Changed
- Breaking changes to article processing pipeline

## [2.3.2] - 2025-10-15
### Fixed
- Minor bug fixes and improvements

[unreleased]: https://github.com/starfysh-tech/AppletScriptorium/compare/v4.0.1...HEAD
[4.0.1]: https://github.com/starfysh-tech/AppletScriptorium/compare/v4.0.0...v4.0.1
[4.0.0]: https://github.com/starfysh-tech/AppletScriptorium/compare/v3.1.0...v4.0.0
[3.1.0]: https://github.com/starfysh-tech/AppletScriptorium/compare/v3.0.0...v3.1.0
[3.0.0]: https://github.com/starfysh-tech/AppletScriptorium/compare/v2.3.2...v3.0.0
[2.3.2]: https://github.com/starfysh-tech/AppletScriptorium/releases/tag/v2.3.2
