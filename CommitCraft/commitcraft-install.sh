#!/usr/bin/env bash
# CommitCraft v5 - Intelligent Installer
#
# Automatically detects current state and presents appropriate options:
# - Not installed: Offers to install
# - Legacy detected: Shows old files, cleans up and installs
# - Updates available: Shows what changed, offers to update
# - Up to date: Offers to reinstall or uninstall
#
# Uses content hashing (MD5) to detect changes accurately.
# No timestamp comparison - works reliably after git pull/checkout.

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Script directory (source files live here)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Install destination
INSTALL_DIR="$HOME/.claude/skills/commitcraft"

# File manifest: parallel arrays for Bash 3.2 compatibility (macOS default)
# SRC_FILES: paths relative to SCRIPT_DIR
# DEST_NAMES: paths relative to INSTALL_DIR
SRC_FILES=(
    "SKILL.md"
    "commitcraft-setup.sh"
    "commitcraft-issues.sh"
    "commitcraft-release-analyze.sh"
    "workflows/commit.md"
    "workflows/push.md"
    "workflows/pr.md"
    "workflows/release.md"
    "workflows/setup.md"
    "workflows/check.md"
    "templates/commitlint.config.js"
    "templates/.commitlintrc.yml"
    "templates/.gitleaks.toml"
    "templates/.pre-commit-config.yaml"
    "templates/commitlint-ci.yml"
    "templates/release-please-config.json"
    "templates/release-please.yml"
    "templates/gitleaks.yml"
)
DEST_NAMES=(
    "SKILL.md"
    "commitcraft-setup.sh"
    "commitcraft-issues.sh"
    "commitcraft-release-analyze.sh"
    "workflows/commit.md"
    "workflows/push.md"
    "workflows/pr.md"
    "workflows/release.md"
    "workflows/setup.md"
    "workflows/check.md"
    "templates/commitlint.config.js"
    "templates/.commitlintrc.yml"
    "templates/.gitleaks.toml"
    "templates/.pre-commit-config.yaml"
    "templates/commitlint-ci.yml"
    "templates/release-please-config.json"
    "templates/release-please.yml"
    "templates/gitleaks.yml"
)

# Legacy files from v4.x (may exist on other users' machines)
LEGACY_FILES=(
    "$HOME/.claude/scripts/commitcraft-analyze.sh"
    "$HOME/.claude/scripts/commitcraft-release-analyze.sh"
    "$HOME/.claude/commands/commitcraft-push.md"
    "$HOME/.claude/commands/commitcraft-release.md"
)

# ============================================================================
# Utility Functions
# ============================================================================

# Cross-platform hash function (MD5)
get_hash() {
    local file="$1"
    if [ ! -f "$file" ]; then
        echo "missing"
        return
    fi
    if command -v md5 >/dev/null 2>&1; then
        md5 -q "$file" 2>/dev/null || echo "error"
    elif command -v md5sum >/dev/null 2>&1; then
        md5sum "$file" 2>/dev/null | cut -d' ' -f1 || echo "error"
    else
        echo "error"
    fi
}

# Draw box header
draw_header() {
    local title="$1"
    echo ""
    echo -e "${BOLD}================================================================${NC}"
    echo -e "${BOLD}  $title${NC}"
    echo -e "${BOLD}================================================================${NC}"
}

# ============================================================================
# Legacy Detection & Cleanup
# ============================================================================

has_legacy_files() {
    for f in "${LEGACY_FILES[@]}"; do
        if [ -f "$f" ]; then
            return 0
        fi
    done
    return 1
}

cleanup_legacy() {
    local found=0
    for f in "${LEGACY_FILES[@]}"; do
        if [ -f "$f" ]; then
            rm "$f"
            echo -e "  ${CYAN}↻${NC} Removed legacy: $(basename "$f")"
            found=1
        fi
    done

    # Clean up empty scripts/ dir (only if empty — no other tools)
    if [ -d "$HOME/.claude/scripts" ] && [ -z "$(ls -A "$HOME/.claude/scripts")" ]; then
        rmdir "$HOME/.claude/scripts"
        echo -e "  ${CYAN}↻${NC} Removed empty scripts/ directory"
    fi

    # Do NOT touch commands/ — contains non-CommitCraft files

    # Remove shell aliases added by old installer (other users)
    for rc in "$HOME/.zshrc" "$HOME/.bashrc"; do
        if [ -f "$rc" ] && grep -q "alias commitcraft-init=" "$rc" 2>/dev/null; then
            sed -i.bak '/# CommitCraft alias/d' "$rc"
            sed -i.bak '/alias commitcraft-init=/d' "$rc"
            echo -e "  ${CYAN}↻${NC} Removed commitcraft-init alias from $(basename "$rc")"
        fi
    done

    # Remove git template hook (from very old installs)
    if [ -f "$HOME/.git-templates/hooks/post-checkout" ]; then
        rm "$HOME/.git-templates/hooks/post-checkout"
        echo -e "  ${CYAN}↻${NC} Removed git template hook"
    fi
    if git config --global --get init.templatedir >/dev/null 2>&1; then
        git config --global --unset init.templatedir
        echo -e "  ${CYAN}↻${NC} Removed git templatedir config"
    fi

    if [ $found -eq 1 ]; then
        echo ""
    fi
}

# ============================================================================
# State Detection
# ============================================================================

detect_state() {
    # Check for legacy files first (can coexist with new install)
    if has_legacy_files; then
        echo "legacy_detected"
        return
    fi

    # Check if install dir exists
    if [ ! -d "$INSTALL_DIR" ]; then
        echo "not_installed"
        return
    fi

    local missing=0
    local outdated=0
    local total=${#SRC_FILES[@]}

    for ((i=0; i<total; i++)); do
        local src_path="$SCRIPT_DIR/${SRC_FILES[$i]}"
        local dst_path="$INSTALL_DIR/${DEST_NAMES[$i]}"

        local src_hash=$(get_hash "$src_path")
        local dst_hash=$(get_hash "$dst_path")

        if [ "$dst_hash" = "missing" ]; then
            missing=$((missing + 1))
        elif [ "$src_hash" != "$dst_hash" ]; then
            outdated=$((outdated + 1))
        fi
    done

    if [ $missing -eq $total ]; then
        echo "not_installed"
    elif [ $outdated -gt 0 ] || [ $missing -gt 0 ]; then
        echo "updates_available"
    else
        echo "up_to_date"
    fi
}

# ============================================================================
# Display Functions — Grouped TUI
# ============================================================================

# Compute aggregate status for a group of file indices
# Prints: "current", "update", or "missing"
group_status() {
    local -a indices=("$@")
    local has_missing=0
    local has_outdated=0

    for i in "${indices[@]}"; do
        local src_path="$SCRIPT_DIR/${SRC_FILES[$i]}"
        local dst_path="$INSTALL_DIR/${DEST_NAMES[$i]}"
        local src_hash=$(get_hash "$src_path")
        local dst_hash=$(get_hash "$dst_path")

        if [ "$dst_hash" = "missing" ]; then
            has_missing=1
        elif [ "$src_hash" != "$dst_hash" ]; then
            has_outdated=1
        fi
    done

    if [ $has_missing -eq 1 ]; then
        echo "missing"
    elif [ $has_outdated -eq 1 ]; then
        echo "update"
    else
        echo "current"
    fi
}

# Print a grouped status line
print_group_line() {
    local label="$1"
    local status="$2"
    case "$status" in
        current)  echo -e "  ${GREEN}✓${NC} $label ${GREEN}(current)${NC}" ;;
        update)   echo -e "  ${YELLOW}↻${NC} $label ${CYAN}(update available)${NC}" ;;
        missing)  echo -e "  ${RED}○${NC} $label ${YELLOW}(not installed)${NC}" ;;
    esac
}

show_file_status() {
    echo ""
    # SKILL.md — index 0
    local skill_status=$(group_status 0)
    print_group_line "SKILL.md" "$skill_status"

    # scripts (3) — indices 1 2 3
    local scripts_status=$(group_status 1 2 3)
    print_group_line "scripts (3)" "$scripts_status"

    # workflows/ (6) — indices 4 5 6 7 8 9
    local wf_status=$(group_status 4 5 6 7 8 9)
    print_group_line "workflows/ (6)" "$wf_status"

    # templates/ (8) — indices 10 11 12 13 14 15 16 17
    local tmpl_status=$(group_status 10 11 12 13 14 15 16 17)
    print_group_line "templates/ (8)" "$tmpl_status"

    echo ""
}

# Show individual file details for updates/diffs
show_file_details() {
    echo ""
    local total=${#SRC_FILES[@]}
    for ((i=0; i<total; i++)); do
        local src_path="$SCRIPT_DIR/${SRC_FILES[$i]}"
        local dst_path="$INSTALL_DIR/${DEST_NAMES[$i]}"
        local display_name="${DEST_NAMES[$i]}"

        local src_hash=$(get_hash "$src_path")
        local dst_hash=$(get_hash "$dst_path")

        if [ "$dst_hash" = "missing" ]; then
            echo -e "  ${RED}○${NC} $display_name ${YELLOW}(not installed)${NC}"
        elif [ "$src_hash" != "$dst_hash" ]; then
            echo -e "  ${YELLOW}↻${NC} $display_name ${CYAN}(update available)${NC}"
        fi
    done
    echo ""
}

show_not_installed() {
    clear 2>/dev/null || printf '\n\n\n'
    draw_header "CommitCraft v5 — Not Installed"
    echo ""
    echo -e "Status: ${RED}○${NC} Not installed"
    echo ""
    echo "This will install to: ~/.claude/skills/commitcraft/"
    echo "  • SKILL.md (skill definition)"
    echo "  • scripts (3 — setup, issues, release-analyze)"
    echo "  • workflows/ (6 — commit, push, pr, release, setup, check)"
    echo "  • templates/ (8 — commitlint, gitleaks, pre-commit, CI)"
    echo ""
    echo "Invocation: /commitcraft [commit|push|pr|release|setup|check]"
    echo ""
    echo "Options:"
    echo -e "  ${BOLD}1.${NC} Install"
    echo -e "  ${BOLD}2.${NC} Exit"
    echo ""
}

show_legacy_detected() {
    clear 2>/dev/null || printf '\n\n\n'
    draw_header "CommitCraft v5 — Legacy Install Detected"
    echo ""
    echo -e "Status: ${YELLOW}●${NC} Legacy v4.x files found"
    echo ""
    echo "Legacy files to remove:"
    for f in "${LEGACY_FILES[@]}"; do
        if [ -f "$f" ]; then
            echo -e "  ${YELLOW}↻${NC} $f"
        fi
    done
    echo ""
    echo "Then install to: ~/.claude/skills/commitcraft/"
    echo ""
    echo "Options:"
    echo -e "  ${BOLD}1.${NC} Clean up legacy + install v5"
    echo -e "  ${BOLD}2.${NC} Exit"
    echo ""
}

show_updates_available() {
    clear 2>/dev/null || printf '\n\n\n'
    draw_header "CommitCraft v5 — Updates Available"
    echo ""

    local update_count=0
    local total=${#SRC_FILES[@]}
    for ((i=0; i<total; i++)); do
        local src_path="$SCRIPT_DIR/${SRC_FILES[$i]}"
        local dst_path="$INSTALL_DIR/${DEST_NAMES[$i]}"
        local src_hash=$(get_hash "$src_path")
        local dst_hash=$(get_hash "$dst_path")
        if [ "$dst_hash" = "missing" ] || [ "$src_hash" != "$dst_hash" ]; then
            update_count=$((update_count + 1))
        fi
    done

    echo -e "Status: ${YELLOW}●${NC} Installed ($update_count updates available)"
    show_file_status
    echo "Options:"
    echo -e "  ${BOLD}1.${NC} Update ($update_count files)"
    echo -e "  ${BOLD}2.${NC} Show changed files"
    echo -e "  ${BOLD}3.${NC} Show diffs"
    echo -e "  ${BOLD}4.${NC} Reinstall all (force)"
    echo -e "  ${BOLD}5.${NC} Uninstall"
    echo -e "  ${BOLD}6.${NC} Exit"
    echo ""
}

show_up_to_date() {
    clear 2>/dev/null || printf '\n\n\n'
    draw_header "CommitCraft v5 — Up to Date"
    echo ""
    echo -e "Status: ${GREEN}✓${NC} Installed (all files current)"
    show_file_status
    echo "Options:"
    echo -e "  ${BOLD}1.${NC} Reinstall all (force)"
    echo -e "  ${BOLD}2.${NC} Uninstall"
    echo -e "  ${BOLD}3.${NC} Exit"
    echo ""
}

# ============================================================================
# Operation Functions
# ============================================================================

install_or_update() {
    local force="${1:-false}"

    echo ""
    echo "Installing/updating files..."
    echo ""

    # Create directories
    mkdir -p "$INSTALL_DIR/workflows"
    mkdir -p "$INSTALL_DIR/templates"

    local total=${#SRC_FILES[@]}
    for ((i=0; i<total; i++)); do
        local src_path="$SCRIPT_DIR/${SRC_FILES[$i]}"
        local dst_path="$INSTALL_DIR/${DEST_NAMES[$i]}"
        local display_name="${DEST_NAMES[$i]}"

        local src_hash=$(get_hash "$src_path")
        local dst_hash=$(get_hash "$dst_path")

        if [ "$force" = "true" ] || [ "$dst_hash" = "missing" ] || [ "$src_hash" != "$dst_hash" ]; then
            cp "$src_path" "$dst_path"

            # Set executable for shell scripts
            if [[ "$dst_path" == *.sh ]]; then
                chmod +x "$dst_path"
            fi

            if [ "$dst_hash" = "missing" ]; then
                echo -e "  ${GREEN}✓${NC} Installed $display_name"
            else
                echo -e "  ${CYAN}↻${NC} Updated $display_name"
            fi
        else
            echo -e "    Skipped $display_name (already current)"
        fi
    done

    echo ""
    echo -e "${GREEN}✓${NC} Installation/update complete"
    echo ""
    echo "Invoke in Claude Code: /commitcraft [commit|push|pr|release|setup|check]"
    echo ""
    read -p "Press Enter to exit..."
    exit 0
}

show_diffs() {
    if ! command -v delta >/dev/null 2>&1; then
        echo ""
        echo -e "${RED}Error: delta pager not found${NC}"
        echo "Install delta: brew install git-delta"
        echo ""
        read -p "Press Enter to continue..."
        return
    fi

    echo ""
    echo "Showing diffs for changed files..."
    echo ""

    local has_diffs=false
    local total=${#SRC_FILES[@]}

    for ((i=0; i<total; i++)); do
        local src_path="$SCRIPT_DIR/${SRC_FILES[$i]}"
        local dst_path="$INSTALL_DIR/${DEST_NAMES[$i]}"
        local display_name="${DEST_NAMES[$i]}"

        local src_hash=$(get_hash "$src_path")
        local dst_hash=$(get_hash "$dst_path")

        if [ "$dst_hash" = "missing" ]; then
            has_diffs=true
            echo -e "${BOLD}━━━ $display_name ${YELLOW}(new file)${NC} ━━━${NC}"
            echo "Will be installed to: $dst_path"
            echo ""
        elif [ "$src_hash" != "$dst_hash" ]; then
            has_diffs=true
            echo -e "${BOLD}━━━ $display_name ━━━${NC}"
            echo ""
            diff -u "$dst_path" "$src_path" | delta --paging=never || true
            echo ""
        fi
    done

    if [ "$has_diffs" = "false" ]; then
        echo "No diffs to show (all files are current)"
    fi

    echo ""
    read -p "Press Enter to continue..."
}

uninstall() {
    echo ""
    echo -e "${YELLOW}Warning: This will remove all CommitCraft files from ~/.claude/skills/commitcraft/${NC}"
    echo ""
    read -p "Are you sure? [y/N] " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Uninstall cancelled"
        return
    fi

    echo ""
    echo "Uninstalling..."
    echo ""

    # Remove files from manifest (file-by-file, not rm -rf)
    local total=${#DEST_NAMES[@]}
    for ((i=0; i<total; i++)); do
        local dst_path="$INSTALL_DIR/${DEST_NAMES[$i]}"
        if [ -f "$dst_path" ]; then
            rm "$dst_path"
            echo -e "  ${GREEN}✓${NC} Removed ${DEST_NAMES[$i]}"
        fi
    done

    # Remove empty subdirectories (use ls -A to catch dotfiles)
    for subdir in "templates" "workflows"; do
        local dir="$INSTALL_DIR/$subdir"
        if [ -d "$dir" ] && [ -z "$(ls -A "$dir")" ]; then
            rmdir "$dir"
            echo -e "  ${GREEN}✓${NC} Removed empty $subdir/"
        fi
    done

    # Remove install dir only if empty
    if [ -d "$INSTALL_DIR" ] && [ -z "$(ls -A "$INSTALL_DIR")" ]; then
        rmdir "$INSTALL_DIR"
        echo -e "  ${GREEN}✓${NC} Removed commitcraft/ directory"
    fi

    # Remove git template hook (legacy cleanup)
    if [ -f "$HOME/.git-templates/hooks/post-checkout" ]; then
        rm "$HOME/.git-templates/hooks/post-checkout"
        echo -e "  ${GREEN}✓${NC} Removed git template hook"
    fi
    if git config --global --get init.templatedir >/dev/null 2>&1; then
        git config --global --unset init.templatedir
        echo -e "  ${GREEN}✓${NC} Removed git templatedir config"
    fi

    echo ""
    echo -e "${GREEN}✓${NC} Uninstall complete"
    echo ""
    read -p "Press Enter to exit..."
    exit 0
}

# ============================================================================
# Main Menu Loop
# ============================================================================

main() {
    while true; do
        local state=$(detect_state)

        case "$state" in
            not_installed)
                show_not_installed
                read -p "Choice: " choice
                case "$choice" in
                    1)
                        cleanup_legacy  # no-op if nothing found
                        install_or_update false
                        ;;
                    2|q|Q) exit 0 ;;
                    *) echo "Invalid choice" ; sleep 1 ;;
                esac
                ;;

            legacy_detected)
                show_legacy_detected
                read -p "Choice: " choice
                case "$choice" in
                    1)
                        echo ""
                        echo "Cleaning up legacy files..."
                        cleanup_legacy
                        install_or_update false
                        ;;
                    2|q|Q) exit 0 ;;
                    *) echo "Invalid choice" ; sleep 1 ;;
                esac
                ;;

            updates_available)
                show_updates_available
                read -p "Choice: " choice
                case "$choice" in
                    1) install_or_update false ;;
                    2) show_file_details ; read -p "Press Enter to continue..." ;;
                    3) show_diffs ;;
                    4) install_or_update true ;;
                    5) uninstall ;;
                    6|q|Q) exit 0 ;;
                    *) echo "Invalid choice" ; sleep 1 ;;
                esac
                ;;

            up_to_date)
                show_up_to_date
                read -p "Choice: " choice
                case "$choice" in
                    1) install_or_update true ;;
                    2) uninstall ;;
                    3|q|Q) exit 0 ;;
                    *) echo "Invalid choice" ; sleep 1 ;;
                esac
                ;;
        esac
    done
}

# Run main menu
main
