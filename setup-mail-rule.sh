#!/usr/bin/env bash
set -euo pipefail

# Google Alert Intelligence - Mail Rule Setup Helper
# Configures AppleScript for Mail.app automation

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIL_SCRIPTS_DIR="$HOME/Library/Application Scripts/com.apple.mail"
TEMPLATE_FILE="$REPO_ROOT/Summarizer/templates/process-alert.scpt"
TARGET_FILE="$MAIL_SCRIPTS_DIR/process-alert.scpt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[!]${NC} $*"
}

log_error() {
    echo -e "${RED}[✗]${NC} $*"
}

echo ""
log_info "Google Alert Intelligence - Mail Rule Setup"
echo "=============================================="
echo ""

# Check if template exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    log_error "Template not found: $TEMPLATE_FILE"
    log_info "Run ./install.sh first to set up templates"
    exit 1
fi

# Create Mail scripts directory if needed
if [ ! -d "$MAIL_SCRIPTS_DIR" ]; then
    log_info "Creating Mail scripts directory..."
    mkdir -p "$MAIL_SCRIPTS_DIR"
    log_success "Created: $MAIL_SCRIPTS_DIR"
fi

# Prompt for email address
echo ""
log_info "Enter your email address for digest delivery:"
read -r -p "Email: " USER_EMAIL

if [ -z "$USER_EMAIL" ]; then
    log_error "Email address cannot be empty"
    exit 1
fi

# Validate email format (basic check)
if ! echo "$USER_EMAIL" | grep -qE '^[^@]+@[^@]+\.[^@]+$'; then
    log_warn "Email format may be invalid: $USER_EMAIL"
    read -r -p "Continue anyway? (y/n): " CONTINUE
    if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
        exit 1
    fi
fi

echo ""
log_info "Detecting Python installations..."

# Find all Python 3 installations
PYTHON_PATHS=()
PYTHON_VERSIONS=()
PYTHON_DEPS_STATUS=()
PYTHON_PEP668_BLOCKED=()
PYTHON_FRIENDLY_NAMES=()
PYTHON_SIMPLE_STATUS=()

# Common Python 3 locations
SEARCH_PATHS=(
    "/usr/bin/python3"
    "/usr/local/bin/python3"
    "/opt/homebrew/bin/python3"
    "$HOME/miniconda/bin/python3"
    "$HOME/miniconda3/bin/python3"
    "$HOME/anaconda/bin/python3"
    "$HOME/anaconda3/bin/python3"
)

# Also check PATH
if command -v python3 &> /dev/null; then
    PATH_PYTHON=$(which python3)
    SEARCH_PATHS+=("$PATH_PYTHON")
fi

# Parse required packages from requirements.txt (excluding pytest which is only for development)
REQUIREMENTS_FILE="$REPO_ROOT/Summarizer/requirements.txt"
REQUIRED_PACKAGES=()
if [ -f "$REQUIREMENTS_FILE" ]; then
    while IFS= read -r line; do
        # Skip comments, empty lines, and pytest
        if [[ ! "$line" =~ ^# ]] && [[ -n "$line" ]] && [[ ! "$line" =~ ^pytest ]]; then
            # Extract package name (before >= or <)
            pkg_name=$(echo "$line" | sed -E 's/[><=].*//' | xargs)
            if [ -n "$pkg_name" ]; then
                REQUIRED_PACKAGES+=("$pkg_name")
            fi
        fi
    done < "$REQUIREMENTS_FILE"
else
    log_error "Requirements file not found: $REQUIREMENTS_FILE"
    exit 1
fi

# Check each Python installation
for py_path in "${SEARCH_PATHS[@]}"; do
    if [ -x "$py_path" ]; then
        # Get version
        version=$("$py_path" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || echo "unknown")

        # Create user-friendly name based on path
        friendly_name=""
        if [[ "$py_path" == "/usr/bin/python3" ]]; then
            friendly_name="Apple System Python $version"
        elif [[ "$py_path" == "/usr/local/bin/python3" ]]; then
            friendly_name="Homebrew Python $version"
        elif [[ "$py_path" == "/opt/homebrew/bin/python3" ]]; then
            friendly_name="Homebrew Python $version"
        elif [[ "$py_path" == *"miniconda"* ]]; then
            friendly_name="Miniconda Python $version"
        elif [[ "$py_path" == *"anaconda"* ]]; then
            friendly_name="Anaconda Python $version"
        else
            friendly_name="Python $version (at $py_path)"
        fi

        # Check for PEP 668 (externally-managed environment) on Python 3.14+
        major_minor=$(echo "$version" | grep -oE '^[0-9]+\.[0-9]+' || echo "0.0")
        is_pep668_blocked=false
        if [[ "$py_path" == "/usr/local/bin/python3" ]] || [[ "$py_path" == "/opt/homebrew/bin/python3" ]]; then
            # Homebrew Python 3.14+ has PEP 668 restrictions
            if awk -v ver="$major_minor" 'BEGIN {exit !(ver >= 3.14)}'; then
                is_pep668_blocked=true
            fi
        fi

        # Check for required packages (skip if PEP 668 blocked and has no deps)
        missing_packages=()
        if [ "$is_pep668_blocked" = false ]; then
            for pkg in "${REQUIRED_PACKAGES[@]}"; do
                if ! "$py_path" -m pip show "$pkg" &> /dev/null; then
                    missing_packages+=("$pkg")
                fi
            done
        fi

        # Determine status with user-friendly messages
        if [ "$is_pep668_blocked" = true ]; then
            # Check if packages are already installed despite PEP 668
            has_any_deps=false
            for pkg in "${REQUIRED_PACKAGES[@]}"; do
                if "$py_path" -m pip show "$pkg" &> /dev/null; then
                    has_any_deps=true
                    break
                fi
            done

            if [ "$has_any_deps" = true ]; then
                status="Ready to use, but can't install new packages"
                simple_status="ready"
            else
                status="Newer version has restrictions - not recommended"
                simple_status="not_recommended"
            fi
            indicator="⚠"
        elif [ ${#missing_packages[@]} -eq 0 ]; then
            status="Ready to use"
            simple_status="ready"
            indicator="✓"
        elif [ ${#missing_packages[@]} -eq ${#REQUIRED_PACKAGES[@]} ]; then
            num_packages=${#REQUIRED_PACKAGES[@]}
            status="Needs $num_packages packages installed"
            simple_status="needs_setup"
            indicator="○"
        else
            num_missing=${#missing_packages[@]}
            status="Needs $num_missing packages installed"
            simple_status="needs_setup"
            indicator="○"
        fi

        # Add to arrays (avoid duplicates)
        if [[ ${#PYTHON_PATHS[@]} -eq 0 ]] || [[ ! " ${PYTHON_PATHS[@]} " =~ " ${py_path} " ]]; then
            PYTHON_PATHS+=("$py_path")
            PYTHON_VERSIONS+=("$version")
            PYTHON_DEPS_STATUS+=("$status")
            PYTHON_PEP668_BLOCKED+=("$is_pep668_blocked")
            PYTHON_FRIENDLY_NAMES+=("$friendly_name")
            PYTHON_SIMPLE_STATUS+=("$simple_status")
        fi
    fi
done

# Check if any Python installations found
if [ ${#PYTHON_PATHS[@]} -eq 0 ]; then
    log_error "No Python 3 installations found"
    log_info "Install Python 3 via Homebrew: brew install python3"
    exit 1
fi

echo ""
log_info "Checking available Python installations..."

# Determine recommended Python with new priority logic:
# 1. Python with all dependencies (✓) and not PEP 668 blocked
# 2. Homebrew Python 3.11 or older (not PEP 668 blocked)
# 3. System Python (/usr/bin/python3)
# 4. Any other available Python
RECOMMENDED_IDX=-1

# Priority 1: Python with all dependencies found
for i in "${!PYTHON_PATHS[@]}"; do
    simple_stat="${PYTHON_SIMPLE_STATUS[$i]}"
    if [[ "$simple_stat" == "ready" ]]; then
        RECOMMENDED_IDX=$i
        break
    fi
done

# Priority 2: Homebrew Python (not PEP 668 blocked)
if [[ $RECOMMENDED_IDX -eq -1 ]]; then
    for i in "${!PYTHON_PATHS[@]}"; do
        path="${PYTHON_PATHS[$i]}"
        is_blocked="${PYTHON_PEP668_BLOCKED[$i]}"
        if [[ "$is_blocked" == "false" ]] && ([[ "$path" == "/usr/local/bin/python3" ]] || [[ "$path" == "/opt/homebrew/bin/python3" ]]); then
            RECOMMENDED_IDX=$i
            break
        fi
    done
fi

# Priority 3: System Python
if [[ $RECOMMENDED_IDX -eq -1 ]]; then
    for i in "${!PYTHON_PATHS[@]}"; do
        if [[ "${PYTHON_PATHS[$i]}" == "/usr/bin/python3" ]]; then
            RECOMMENDED_IDX=$i
            break
        fi
    done
fi

# Priority 4: Any available Python
if [[ $RECOMMENDED_IDX -eq -1 ]] && [[ ${#PYTHON_PATHS[@]} -gt 0 ]]; then
    RECOMMENDED_IDX=0
fi

# Count installations by status
READY_COUNT=0
READY_IDX=-1
NEEDS_SETUP_COUNT=0
NOT_RECOMMENDED_COUNT=0

for i in "${!PYTHON_SIMPLE_STATUS[@]}"; do
    simple_stat="${PYTHON_SIMPLE_STATUS[$i]}"
    if [[ "$simple_stat" == "ready" ]]; then
        READY_COUNT=$((READY_COUNT + 1))
        if [[ $READY_IDX -eq -1 ]]; then
            READY_IDX=$i
        fi
    elif [[ "$simple_stat" == "needs_setup" ]]; then
        NEEDS_SETUP_COUNT=$((NEEDS_SETUP_COUNT + 1))
    elif [[ "$simple_stat" == "not_recommended" ]]; then
        NOT_RECOMMENDED_COUNT=$((NOT_RECOMMENDED_COUNT + 1))
    fi
done

# Display installations grouped by status
echo ""

# Show ready installations first
if [[ $READY_COUNT -gt 0 ]]; then
    echo -e "${GREEN}✓ Ready to use:${NC}"
    echo ""
    for i in "${!PYTHON_SIMPLE_STATUS[@]}"; do
        if [[ "${PYTHON_SIMPLE_STATUS[$i]}" == "ready" ]]; then
            num=$((i + 1))
            friendly_name="${PYTHON_FRIENDLY_NAMES[$i]}"
            status="${PYTHON_DEPS_STATUS[$i]}"

            recommended_marker=""
            if [[ $i -eq $RECOMMENDED_IDX ]]; then
                recommended_marker=" ${GREEN}← Recommended${NC}"
            fi

            echo -e "  ${GREEN}[$num]${NC} $friendly_name$recommended_marker"
            echo "      → All packages already installed"
            echo ""
        fi
    done
fi

# Show installations that need setup
if [[ $NEEDS_SETUP_COUNT -gt 0 ]]; then
    echo -e "${YELLOW}○ Needs setup:${NC}"
    echo ""
    for i in "${!PYTHON_SIMPLE_STATUS[@]}"; do
        if [[ "${PYTHON_SIMPLE_STATUS[$i]}" == "needs_setup" ]]; then
            num=$((i + 1))
            friendly_name="${PYTHON_FRIENDLY_NAMES[$i]}"
            status="${PYTHON_DEPS_STATUS[$i]}"

            echo -e "  ${YELLOW}[$num]${NC} $friendly_name"
            echo "      → $status"
            echo ""
        fi
    done
fi

# Show not recommended installations
if [[ $NOT_RECOMMENDED_COUNT -gt 0 ]]; then
    echo -e "${YELLOW}⚠ Not recommended:${NC}"
    echo ""
    for i in "${!PYTHON_SIMPLE_STATUS[@]}"; do
        if [[ "${PYTHON_SIMPLE_STATUS[$i]}" == "not_recommended" ]]; then
            num=$((i + 1))
            friendly_name="${PYTHON_FRIENDLY_NAMES[$i]}"
            status="${PYTHON_DEPS_STATUS[$i]}"

            echo -e "  ${YELLOW}[$num]${NC} $friendly_name"
            echo "      → $status"
            echo ""
        fi
    done
fi

if [[ $READY_COUNT -gt 0 ]]; then
    echo ""
    if [[ $READY_IDX -ge 0 ]]; then
        ready_num=$((READY_IDX + 1))
        log_info "Select which Python to use (or press Enter for [$ready_num]):"
    fi
else
    echo ""
    echo -e "  ${YELLOW}[0] Install fresh Python 3.11 via Homebrew${NC} (recommended)"
    echo "      → Avoids compatibility issues with newer versions"
    echo ""
    log_info "Select which Python to use, or choose [0] to install a fresh copy:"
fi

# Prompt user to select Python installation
echo ""
if [[ $READY_COUNT -eq 0 ]]; then
    # Offer Homebrew install as option 0
    read -r -p "Your choice: " SELECTED_NUM

    if [[ "$SELECTED_NUM" == "0" ]]; then
        echo ""
        log_info "Installing Python 3.11 via Homebrew..."
        if brew install python@3.11; then
            log_success "Python 3.11 installed successfully!"
            log_info "Re-scanning Python installations..."
            # Re-run the setup script
            exec "$0"
        else
            log_error "Failed to install Python 3.11 via Homebrew."
            log_info "Please install manually: brew install python@3.11"
            exit 1
        fi
    fi
elif [[ $RECOMMENDED_IDX -ge 0 ]]; then
    default_choice=$((RECOMMENDED_IDX + 1))
    read -r -p "Your choice: " SELECTED_NUM
    SELECTED_NUM=${SELECTED_NUM:-$default_choice}
else
    read -r -p "Your choice: " SELECTED_NUM
fi

# Validate selection
if ! [[ "$SELECTED_NUM" =~ ^[0-9]+$ ]] || [ "$SELECTED_NUM" -lt 1 ] || [ "$SELECTED_NUM" -gt ${#PYTHON_PATHS[@]} ]; then
    log_error "Invalid selection: $SELECTED_NUM"
    exit 1
fi

SELECTED_PYTHON="${PYTHON_PATHS[$((SELECTED_NUM - 1))]}"
SELECTED_STATUS="${PYTHON_DEPS_STATUS[$((SELECTED_NUM - 1))]}"

log_success "Selected: $SELECTED_PYTHON"
log_info "$SELECTED_STATUS"

# Offer to install dependencies if missing
if [[ "$SELECTED_STATUS" == *"✗"* ]] || [[ "$SELECTED_STATUS" == *"⚠"* ]]; then
    echo ""
    log_warn "The selected Python installation is missing some or all dependencies."
    echo ""
    log_info "Required packages from Summarizer/requirements.txt:"
    cat "$REQUIREMENTS_FILE" | grep -v "^#" | grep -v "^pytest" | grep -v "^$"
    echo ""
    log_info "Install command: $SELECTED_PYTHON -m pip install --user -r Summarizer/requirements.txt"
    echo ""
    read -r -p "Install missing dependencies now? (y/n): " INSTALL_DEPS

    if [ "$INSTALL_DEPS" = "y" ] || [ "$INSTALL_DEPS" = "Y" ]; then
        echo ""
        log_info "Installing dependencies from requirements.txt..."
        if "$SELECTED_PYTHON" -m pip install --user -r "$REQUIREMENTS_FILE"; then
            log_success "Dependencies installed successfully!"
        else
            log_error "Failed to install dependencies. You may need to install them manually."
            read -r -p "Continue with setup anyway? (y/n): " CONTINUE
            if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
                log_info "Setup cancelled"
                exit 0
            fi
        fi
    else
        echo ""
        log_warn "You'll need to install dependencies manually before the pipeline will work."
        read -r -p "Continue with setup anyway? (y/n): " CONTINUE
        if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
            log_info "Setup cancelled"
            exit 0
        fi
    fi
fi

echo ""
log_info "Configuring AppleScript..."

# Replace {{EMAIL}}, {{REPO_PATH}}, and {{PYTHON_PATH}} placeholders
sed -e "s|{{EMAIL}}|$USER_EMAIL|g" \
    -e "s|{{REPO_PATH}}|$REPO_ROOT|g" \
    -e "s|{{PYTHON_PATH}}|$SELECTED_PYTHON|g" \
    "$TEMPLATE_FILE" > "$TARGET_FILE"

if [ -f "$TARGET_FILE" ]; then
    log_success "AppleScript installed: $TARGET_FILE"
    log_success "Configured for: $USER_EMAIL"
    log_success "Python path: $SELECTED_PYTHON"
    log_success "Repository path: $REPO_ROOT"
else
    log_error "Failed to create AppleScript"
    exit 1
fi

echo ""
log_success "Mail Rule Setup Complete!"
echo ""
echo "Next steps:"
echo ""
echo "1. Open Mail.app"
echo "2. Go to Mail → Settings → Rules"
echo "3. Click 'Add Rule'"
echo "4. Configure:"
echo "   - Description: Process Google Alert"
echo "   - Condition 1: From → Contains → googlealerts-noreply@google.com"
echo "   - Condition 2: Subject → Contains → Google Alert -"
echo "   - Action: Run AppleScript → process-alert.scpt"
echo "5. Click OK"
echo ""
echo "6. Grant Accessibility permissions:"
echo "   - System Settings → Privacy & Security → Accessibility"
echo "   - Add Mail.app and enable"
echo ""
echo "When a Google Alert arrives, the rule will:"
echo "  - Extract article links"
echo "  - Fetch and summarize articles"
echo "  - Generate HTML digest"
echo "  - Send email to: $USER_EMAIL"
echo "  - Mark trigger email as read"
echo ""
echo "For detailed troubleshooting, see: Summarizer/MAIL_RULE_SETUP.md"
echo ""

