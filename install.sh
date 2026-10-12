#!/usr/bin/env bash
set -euo pipefail

# Google Alert Intelligence - Installation Script
# Automates setup for new machines

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_CMD="python3"

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

check_prereq() {
    local cmd="$1"
    local name="$2"
    local install_cmd="$3"

    if command -v "$cmd" >/dev/null 2>&1; then
        log_success "$name found: $(command -v "$cmd")"
        return 0
    else
        log_error "$name not found"
        log_info "Install with: $install_cmd"
        return 1
    fi
}

echo ""
log_info "Google Alert Intelligence - Installation Script"
echo "=================================================="
echo ""

# Step 1: Check prerequisites
log_info "Step 1/6: Checking prerequisites..."
echo ""

PREREQ_OK=true

check_prereq "brew" "Homebrew" "/bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"" || PREREQ_OK=false
check_prereq "python3" "Python 3" "brew install python@3.11" || PREREQ_OK=false
check_prereq "git" "Git" "brew install git" || PREREQ_OK=false

if [ "$PREREQ_OK" = false ]; then
    echo ""
    log_error "Missing prerequisites. Please install the above tools and run this script again."
    exit 1
fi

echo ""

# Step 2: Verify Python version
log_info "Step 2/6: Verifying Python version..."
PYTHON_VERSION=$("$PYTHON_CMD" --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
    log_success "Python $PYTHON_VERSION (>= 3.11 required)"
else
    log_error "Python $PYTHON_VERSION found, but 3.11+ required"
    log_info "Install with: brew install python@3.11"
    exit 1
fi

echo ""

# Step 3: Install Python dependencies
log_info "Step 3/6: Installing Python dependencies into .venv..."
# PEP 668 blocks pip installs into Homebrew Python; the Mail rule calls .venv/bin/python3 directly.
if [ ! -x "$REPO_ROOT/.venv/bin/python3" ] && ! "$PYTHON_CMD" -m venv "$REPO_ROOT/.venv"; then
    log_error "Failed to create .venv with $PYTHON_CMD"
    exit 1
fi
PYTHON_CMD="$REPO_ROOT/.venv/bin/python3"
if ! "$PYTHON_CMD" -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
    log_error ".venv uses Python older than 3.11; remove .venv and rerun ./install.sh"
    exit 1
fi
if "$PYTHON_CMD" -m pip install -q -r "$REPO_ROOT/Summarizer/requirements.txt"; then
    log_success "Python dependencies installed"
else
    log_error "Failed to install Python dependencies"
    log_info "Try manually: .venv/bin/python3 -m pip install -r Summarizer/requirements.txt"
    exit 1
fi

echo ""

# Step 4: Make scripts executable and create directories
log_info "Step 4/6: Configuring filesystem..."

chmod +x "$REPO_ROOT/Summarizer/fetch-alert-source.applescript" 2>/dev/null || true
chmod +x "$REPO_ROOT/Summarizer/bin/run_alert.sh" 2>/dev/null || true
chmod +x "$REPO_ROOT/install.sh" 2>/dev/null || true
chmod +x "$REPO_ROOT/setup-mail-rule.sh" 2>/dev/null || true
chmod +x "$REPO_ROOT/validate.sh" 2>/dev/null || true

mkdir -p "$REPO_ROOT/runs"

log_success "Scripts made executable, runs/ directory created"

echo ""

# Step 5: Run tests
log_info "Step 5/6: Running test suite..."
if "$PYTHON_CMD" -m pytest "$REPO_ROOT/Summarizer/tests" -q; then
    log_success "All tests passed"
else
    log_warn "Some tests failed (non-critical for basic usage)"
    log_info "Run manually to see details: .venv/bin/python3 -m pytest Summarizer/tests -v"
fi

echo ""

# Step 6: Summary and next steps
log_info "Step 6/6: Installation complete!"
echo ""
log_success "Google Alert Intelligence is installed and ready!"
echo ""
echo "Next steps:"
echo ""
echo "  1. Test with sample fixture:"
echo "     .venv/bin/python3 Summarizer/clean-alert.py Summarizer/Samples/google-alert-sample-2025-10-06.eml | head"
echo ""
echo "  2. Set up Mail rule automation (recommended):"
echo "     ./setup-mail-rule.sh"
echo ""
echo "  3. Validate setup (also checks the LM Studio server):"
echo "     ./validate.sh"
echo ""
echo "  4. Run manual test:"
echo "     .venv/bin/python3 -m Summarizer.cli run --output-dir runs/test --max-articles 3 --subject-filter 'Google Alert -'"
echo ""
echo "For complete documentation, see:"
echo "  - docs/SETUP.md (setup, Mail automation, verification)"
echo "  - docs/TROUBLESHOOTING.md (common failures and fixes)"
echo "  - README.md (quick start)"
echo ""
