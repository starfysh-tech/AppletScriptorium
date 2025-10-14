# Release Notes v2.0.1

**Release Date:** 2025-10-14

## Overview

Patch release that fixes broken installation caused by UV package manager migration. Reverts to pip-based installation to restore compatibility with Mail.app automation requirements.

## Bug Fixes

### Installation Fixed
- **Critical:** Reverted UV package manager migration back to pip (9fe8c16)
  - UV doesn't support `pip install --user`, required for Mail automation
  - System Python must install packages to user site-packages without root
  - All installation commands restored to `python3 -m pip install --user`
  - Affects: install.sh, SETUP.md, README.md, CLAUDE.md, AGENTS.md, deploy/README.md

### Technical Details
UV's design philosophy (enforce virtual environments) is incompatible with Mail.app automation constraints:
- Mail rules run in Mail.app's security context
- Cannot activate virtual environments from AppleScript
- Requires system Python with user site-packages installation
- UV's `--system` flag requires root permissions
- UV explicitly doesn't support `--user` flag

## Validation

- ✅ install.sh completes successfully
- ✅ All 21 tests passing
- ✅ Dependencies install to `~/Library/Python/3.11/site-packages/`
- ✅ Mail automation compatibility maintained

## Breaking Changes

None. This release restores the working installation method from v2.0.0.

## Upgrade Instructions

If you installed with UV attempts (v2.0.0 + 4 commits):

```bash
# Pull latest changes
cd ~/Code/AppletScriptorium
git pull

# Reinstall dependencies with pip
python3 -m pip install --user -r Summarizer/requirements.txt

# Verify installation
./validate.sh
```

Fresh installations:
```bash
./install.sh
```

## Files Changed

- `install.sh` - Removed UV prerequisite, restored pip commands
- `SETUP.md` - Updated prerequisites and installation steps
- `README.md` - Updated Quick Start and Getting Started sections
- `CLAUDE.md` - Updated development environment setup
- `AGENTS.md` - Updated build commands
- `Summarizer/deploy/README.md` - Updated deployment instructions

## Known Issues

None.

## Credits

🤖 Generated with [Claude Code](https://claude.com/claude-code)
