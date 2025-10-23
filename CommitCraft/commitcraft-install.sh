#!/usr/bin/env bash
# CommitCraft - Intelligent Installer
#
# Automatically detects current state and presents appropriate options:
# - Not installed: Offers to install
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

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Files managed by this installer (relative to SCRIPT_DIR)
declare -A SOURCE_FILES=(
    ["~/.claude/scripts/commitcraft-analyze.sh"]="commitcraft-analyze.sh"
    ["~/.claude/scripts/commitcraft-init.sh"]="commitcraft-init.sh"
    ["~/.git-templates/hooks/post-checkout"]="post-checkout"
    ["~/.claude/commands/commitcraft-push.md"]="commitcraft-push.md"
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

# Expand tilde in paths
expand_path() {
    local path="$1"
    echo "${path/#\~/$HOME}"
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
# State Detection
# ============================================================================

detect_state() {
    local missing=0
    local outdated=0
    local current=0
    local total=0

    for dest in "${!SOURCE_FILES[@]}"; do
        local src_file="${SOURCE_FILES[$dest]}"
        local src_path="$SCRIPT_DIR/$src_file"
        local dst_path=$(expand_path "$dest")

        total=$((total + 1))

        local src_hash=$(get_hash "$src_path")
        local dst_hash=$(get_hash "$dst_path")

        if [ "$dst_hash" = "missing" ]; then
            missing=$((missing + 1))
        elif [ "$src_hash" != "$dst_hash" ]; then
            outdated=$((outdated + 1))
        else
            current=$((current + 1))
        fi
    done

    # Determine overall state
    if [ $missing -eq $total ]; then
        echo "not_installed"
    elif [ $outdated -gt 0 ] || [ $missing -gt 0 ]; then
        echo "updates_available"
    else
        echo "up_to_date"
    fi
}

# ============================================================================
# Display Functions
# ============================================================================

show_file_status() {
    echo ""
    for dest in "${!SOURCE_FILES[@]}"; do
        local src_file="${SOURCE_FILES[$dest]}"
        local src_path="$SCRIPT_DIR/$src_file"
        local dst_path=$(expand_path "$dest")
        local display_name=$(basename "$dst_path")

        local src_hash=$(get_hash "$src_path")
        local dst_hash=$(get_hash "$dst_path")

        if [ "$dst_hash" = "missing" ]; then
            echo -e "  ${RED}○${NC} $display_name ${YELLOW}(not installed)${NC}"
        elif [ "$src_hash" != "$dst_hash" ]; then
            echo -e "  ${YELLOW}↻${NC} $display_name ${CYAN}(update available)${NC}"
        else
            echo -e "  ${GREEN}✓${NC} $display_name ${GREEN}(current)${NC}"
        fi
    done
    echo ""
}

show_not_installed() {
    clear 2>/dev/null || printf '\n\n\n'
    draw_header "CommitCraft - Not Installed"
    echo ""
    echo -e "Status: ${RED}○${NC} Not installed"
    echo ""
    echo "This will install:"
    echo "  • ~/.claude/scripts/ (2 scripts)"
    echo "  • ~/.claude/commands/ (1 command)"
    echo "  • ~/.git-templates/hooks/post-checkout"
    echo "  • Git config: init.templatedir"
    echo "  • Shell alias (optional)"
    echo ""
    echo "Options:"
    echo -e "  ${BOLD}1.${NC} Install"
    echo -e "  ${BOLD}2.${NC} Exit"
    echo ""
}

show_updates_available() {
    clear 2>/dev/null || printf '\n\n\n'
    draw_header "CommitCraft - Updates Available"
    echo ""

    # Count updates
    local update_count=0
    for dest in "${!SOURCE_FILES[@]}"; do
        local src_file="${SOURCE_FILES[$dest]}"
        local src_path="$SCRIPT_DIR/$src_file"
        local dst_path=$(expand_path "$dest")

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
    echo -e "  ${BOLD}2.${NC} Show diffs"
    echo -e "  ${BOLD}3.${NC} Reinstall all (force)"
    echo -e "  ${BOLD}4.${NC} Uninstall"
    echo -e "  ${BOLD}5.${NC} Exit"
    echo ""
}

show_up_to_date() {
    clear 2>/dev/null || printf '\n\n\n'
    draw_header "CommitCraft - Up to Date"
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
    mkdir -p ~/.claude/scripts
    mkdir -p ~/.claude/commands
    mkdir -p ~/.git-templates/hooks

    # Copy files
    for dest in "${!SOURCE_FILES[@]}"; do
        local src_file="${SOURCE_FILES[$dest]}"
        local src_path="$SCRIPT_DIR/$src_file"
        local dst_path=$(expand_path "$dest")
        local display_name=$(basename "$dst_path")

        local src_hash=$(get_hash "$src_path")
        local dst_hash=$(get_hash "$dst_path")

        if [ "$force" = "true" ] || [ "$dst_hash" = "missing" ] || [ "$src_hash" != "$dst_hash" ]; then
            cp "$src_path" "$dst_path"

            # Set executable for hooks and scripts
            if [[ "$dst_path" == *"/hooks/"* ]] || [[ "$dst_path" == *"/scripts/"* ]]; then
                chmod +x "$dst_path"
            fi

            if [ "$dst_hash" = "missing" ]; then
                echo -e "${GREEN}✓${NC} Installed $display_name"
            else
                echo -e "${CYAN}↻${NC} Updated $display_name"
            fi
        else
            echo -e "  Skipped $display_name (already current)"
        fi
    done

    # Create README.md if missing
    if [ ! -f ~/.claude/README.md ]; then
        cat > ~/.claude/README.md << 'EOF'
# CommitCraft

Your personal Claude Code enhancements.

## Directory Structure

```
~/.claude/
├── scripts/          # Reusable scripts
├── commands/         # Slash commands
└── README.md         # This file
```

## Updating

To check for updates:
```bash
cd ~/path/to/AppletScriptorium/CommitCraft
./install-hooks.sh
```

## Source

Installed from: AppletScriptorium/CommitCraft/
EOF
        echo -e "${GREEN}✓${NC} Created README.md"
    fi

    # Configure git
    local current_template=$(git config --global --get init.templatedir 2>/dev/null || echo "")
    if [ "$current_template" != "~/.git-templates" ]; then
        git config --global init.templatedir '~/.git-templates'
        echo -e "${GREEN}✓${NC} Set git config: init.templatedir"
    fi

    # Shell alias (optional)
    configure_shell_alias

    echo ""
    echo -e "${GREEN}✓${NC} Installation/update complete"
    echo ""
    read -p "Press Enter to exit..."
    exit 0
}

configure_shell_alias() {
    # Detect shell config
    local shell_rc=""
    if [ -f "$HOME/.zshrc" ]; then
        shell_rc="$HOME/.zshrc"
    elif [ -f "$HOME/.bashrc" ]; then
        shell_rc="$HOME/.bashrc"
    fi

    if [ -n "$shell_rc" ] && ! grep -q "alias commitcraft-init=" "$shell_rc" 2>/dev/null; then
        echo ""
        echo "Optional: Add shell alias for convenience"
        echo "Alias: commitcraft-init → ~/.claude/scripts/commitcraft-init.sh"
        echo ""
        read -p "Add alias to $shell_rc? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "" >> "$shell_rc"
            echo "# CommitCraft alias" >> "$shell_rc"
            echo "alias commitcraft-init='~/.claude/scripts/commitcraft-init.sh'" >> "$shell_rc"
            echo -e "${GREEN}✓${NC} Added alias (run 'source $shell_rc' to activate)"
        fi
    fi
}

show_diffs() {
    # Check if delta is available
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

    for dest in "${!SOURCE_FILES[@]}"; do
        local src_file="${SOURCE_FILES[$dest]}"
        local src_path="$SCRIPT_DIR/$src_file"
        local dst_path=$(expand_path "$dest")
        local display_name=$(basename "$dst_path")

        local src_hash=$(get_hash "$src_path")
        local dst_hash=$(get_hash "$dst_path")

        if [ "$dst_hash" = "missing" ]; then
            # Show new files
            has_diffs=true
            echo -e "${BOLD}━━━ $display_name ${YELLOW}(new file)${NC} ━━━${NC}"
            echo ""
            echo "Will be installed to: $dst_path"
            echo ""
        elif [ "$src_hash" != "$dst_hash" ]; then
            # Show diffs for changed files
            has_diffs=true
            echo -e "${BOLD}━━━ $display_name ━━━${NC}"
            echo ""

            # Use delta for syntax-highlighted diffs (disable pager)
            # diff returns 1 when files differ, use || true to prevent script exit
            diff -u "$dst_path" "$src_path" | delta --paging=never || true

            echo ""
        fi
    done

    if [ "$has_diffs" = "false" ]; then
        echo "No diffs to show (all files match or are missing)"
    fi

    echo ""
    read -p "Press Enter to continue..."
}

uninstall() {
    echo ""
    echo -e "${YELLOW}Warning: This will remove all CommitCraft tools${NC}"
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

    # Remove ~/.claude/
    if [ -d ~/.claude ]; then
        rm -rf ~/.claude
        echo -e "${GREEN}✓${NC} Removed ~/.claude/"
    fi

    # Remove git template hook
    if [ -f ~/.git-templates/hooks/post-checkout ]; then
        rm ~/.git-templates/hooks/post-checkout
        echo -e "${GREEN}✓${NC} Removed post-checkout hook"
    fi

    # Remove git config
    if git config --global --get init.templatedir >/dev/null 2>&1; then
        git config --global --unset init.templatedir
        echo -e "${GREEN}✓${NC} Removed git config"
    fi

    # Remove shell aliases
    for rc in ~/.zshrc ~/.bashrc; do
        if [ -f "$rc" ] && grep -q "alias commitcraft-init=" "$rc" 2>/dev/null; then
            sed -i.bak '/# CommitCraft alias/d' "$rc"
            sed -i.bak '/alias commitcraft-init=/d' "$rc"
            echo -e "${GREEN}✓${NC} Removed alias from $rc"
        fi
    done

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
                    1) install_or_update false ;;
                    2|q|Q) exit 0 ;;
                    *) echo "Invalid choice" ; sleep 1 ;;
                esac
                ;;

            updates_available)
                show_updates_available
                read -p "Choice: " choice
                case "$choice" in
                    1) install_or_update false ;;
                    2) show_diffs ;;
                    3) install_or_update true ;;
                    4) uninstall ;;
                    5|q|Q) exit 0 ;;
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
