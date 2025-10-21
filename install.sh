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
log_info "Step 1/8: Checking prerequisites..."
echo ""

PREREQ_OK=true

check_prereq "brew" "Homebrew" "/bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"" || PREREQ_OK=false
check_prereq "python3" "Python 3" "brew install python@3.11" || PREREQ_OK=false
check_prereq "ollama" "Ollama" "brew install ollama" || PREREQ_OK=false
check_prereq "git" "Git" "brew install git" || PREREQ_OK=false

if [ "$PREREQ_OK" = false ]; then
    echo ""
    log_error "Missing prerequisites. Please install the above tools and run this script again."
    exit 1
fi

echo ""

# Step 2: Verify Python version
log_info "Step 2/8: Verifying Python version..."
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
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
log_info "Step 3/8: Installing Python dependencies..."
if $PYTHON_CMD -m pip install --user -r "$REPO_ROOT/Summarizer/requirements.txt"; then
    log_success "Python dependencies installed"
else
    log_error "Failed to install Python dependencies"
    log_info "Try manually: python3 -m pip install --user -r Summarizer/requirements.txt"
    exit 1
fi

echo ""

# Step 4: Start Ollama and pull model
log_info "Step 4/7: Setting up Ollama..."

# Start Ollama service if not running
if ! pgrep -x "ollama" >/dev/null; then
    log_info "Starting Ollama service..."
    brew services start ollama >/dev/null 2>&1
    sleep 3
fi

# Check if model exists
if ollama list | grep -q "qwen3:latest"; then
    log_success "Ollama model 'qwen3:latest' already installed"
else
    log_info "Pulling Ollama model 'qwen3:latest' (this may take a few minutes)..."
    if ollama pull qwen3:latest; then
        log_success "Ollama model installed"
    else
        log_error "Failed to pull Ollama model"
        log_info "Try manually: ollama pull qwen3:latest"
        exit 1
    fi
fi

echo ""

# Step 5: Make scripts executable and create directories
log_info "Step 5/7: Configuring filesystem..."

chmod +x "$REPO_ROOT/Summarizer/fetch-alert-source.applescript" 2>/dev/null || true
chmod +x "$REPO_ROOT/run_workflow.sh" 2>/dev/null || true
chmod +x "$REPO_ROOT/Summarizer/bin/run_alert.sh" 2>/dev/null || true
chmod +x "$REPO_ROOT/install.sh" 2>/dev/null || true
chmod +x "$REPO_ROOT/setup-mail-rule.sh" 2>/dev/null || true
chmod +x "$REPO_ROOT/validate.sh" 2>/dev/null || true

mkdir -p "$REPO_ROOT/runs"

log_success "Scripts made executable, runs/ directory created"

echo ""

# Step 6: Run tests
log_info "Step 6/7: Running test suite (21 tests)..."
if $PYTHON_CMD -m pytest "$REPO_ROOT/Summarizer/tests" -q; then
    log_success "All tests passed"
else
    log_warn "Some tests failed (non-critical for basic usage)"
    log_info "Run manually to see details: python3 -m pytest Summarizer/tests -v"
fi

echo ""

# Step 7: Summary and next steps
log_info "Step 7/7: Installation complete!"
echo ""
log_success "Google Alert Intelligence is installed and ready!"
echo ""
echo "Next steps:"
echo ""
echo "  1. Test with sample fixture:"
echo "     python3 Summarizer/clean-alert.py Summarizer/Samples/google-alert-sample-2025-10-06.eml | head"
echo ""
echo "  2. Set up Mail rule automation (recommended):"
echo "     ./setup-mail-rule.sh"
echo ""
echo "  3. Validate setup:"
echo "     ./validate.sh"
echo ""
echo "  4. Run manual test:"
echo "     python3 -m Summarizer.cli run --output-dir runs/test --max-articles 3 --subject-filter 'Google Alert -'"
echo ""
echo "For complete documentation, see:"
echo "  - SETUP.md (comprehensive setup guide)"
echo "  - MAIL_RULE_SETUP.md (Mail automation)"
echo "  - README.md (quick start)"
echo ""
