#!/usr/bin/env bash
set -euo pipefail

# Google Alert Intelligence - Setup Validator
# Checks that all prerequisites and components are working

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_CMD="python3"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_pass() {
    echo -e "${GREEN}[✓]${NC} $*"
    ((PASS_COUNT++))
}

log_fail() {
    echo -e "${RED}[✗]${NC} $*"
    ((FAIL_COUNT++))
}

log_warn() {
    echo -e "${YELLOW}[!]${NC} $*"
    ((WARN_COUNT++))
}

check_command() {
    local cmd="$1"
    local name="$2"

    if command -v "$cmd" >/dev/null 2>&1; then
        local version=""
        case "$cmd" in
            python3)
                version=$($cmd --version 2>&1 | awk '{print $2}')
                ;;
            ollama)
                version=$($cmd --version 2>&1 | head -1)
                ;;
            *)
                version="installed"
                ;;
        esac
        log_pass "$name: $version"
        return 0
    else
        log_fail "$name not found"
        return 1
    fi
}

echo ""
log_info "Google Alert Intelligence - Setup Validation"
echo "=============================================="
echo ""

# Check 1: System commands
log_info "Checking system commands..."
check_command "brew" "Homebrew"
check_command "python3" "Python 3"
check_command "ollama" "Ollama"
check_command "git" "Git"
check_command "osascript" "AppleScript"
echo ""

# Check 2: Python version
log_info "Checking Python version..."
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
    log_pass "Python $PYTHON_VERSION (>= 3.11 required)"
else
    log_fail "Python $PYTHON_VERSION (need >= 3.11)"
fi
echo ""

# Check 3: Python packages
log_info "Checking Python packages..."
PACKAGES=("beautifulsoup4" "httpx" "readability-lxml" "crawlee" "pytest")
for pkg in "${PACKAGES[@]}"; do
    if $PYTHON_CMD -m pip show "$pkg" >/dev/null 2>&1; then
        log_pass "Python package: $pkg"
    else
        log_fail "Python package missing: $pkg"
    fi
done
echo ""

# Check 4: Playwright
log_info "Checking Playwright..."
if $PYTHON_CMD -c "from playwright.sync_api import sync_playwright; print('OK')" >/dev/null 2>&1; then
    log_pass "Playwright installed"
else
    log_warn "Playwright not installed (needed for Cloudflare-protected sites)"
    log_info "Install with: python3 -m playwright install"
fi
echo ""

# Check 5: Ollama service
log_info "Checking Ollama service..."
if pgrep -x "ollama" >/dev/null; then
    log_pass "Ollama service running"
else
    log_fail "Ollama service not running"
    log_info "Start with: brew services start ollama"
fi

# Check 6: Ollama model
if ollama list 2>/dev/null | grep -q "granite4:tiny-h"; then
    log_pass "Ollama model: granite4:tiny-h"
else
    log_fail "Ollama model not found: granite4:tiny-h"
    log_info "Install with: ollama pull granite4:tiny-h"
fi
echo ""

# Check 7: Repository structure
log_info "Checking repository structure..."
DIRS=("Summarizer" "Summarizer/tests" "Summarizer/Samples" "Summarizer/templates" "runs")
for dir in "${DIRS[@]}"; do
    if [ -d "$REPO_ROOT/$dir" ]; then
        log_pass "Directory exists: $dir"
    else
        log_fail "Directory missing: $dir"
    fi
done
echo ""

# Check 8: Scripts are executable
log_info "Checking script permissions..."
SCRIPTS=("install.sh" "setup-mail-rule.sh" "validate.sh" "run_workflow.sh")
for script in "${SCRIPTS[@]}"; do
    if [ -x "$REPO_ROOT/$script" ]; then
        log_pass "Executable: $script"
    else
        log_warn "Not executable: $script"
        log_info "Fix with: chmod +x $script"
    fi
done
echo ""

# Check 9: Run test suite
log_info "Running test suite..."
if $PYTHON_CMD -m pytest "$REPO_ROOT/Summarizer/tests" -q >/dev/null 2>&1; then
    log_pass "Test suite passed"
else
    log_fail "Test suite failed"
    log_info "Run manually for details: python3 -m pytest Summarizer/tests -v"
fi
echo ""

# Check 10: Mail rule setup (optional)
log_info "Checking Mail rule setup (optional)..."
MAIL_SCRIPT="$HOME/Library/Application Scripts/com.apple.mail/process-alert.scpt"
if [ -f "$MAIL_SCRIPT" ]; then
    log_pass "Mail AppleScript installed"
else
    log_warn "Mail AppleScript not found"
    log_info "Set up with: ./setup-mail-rule.sh"
fi
echo ""

# Summary
echo "=============================================="
echo ""
log_info "Validation Summary:"
echo "  ✓ Passed: $PASS_COUNT"
echo "  ✗ Failed: $FAIL_COUNT"
echo "  ! Warnings: $WARN_COUNT"
echo ""

if [ "$FAIL_COUNT" -eq 0 ]; then
    echo -e "${GREEN}All critical checks passed!${NC}"
    echo ""
    echo "You can now:"
    echo "  - Test with: python3 Summarizer/clean-alert.py Summarizer/Samples/google-alert-sample-2025-10-06.eml | head"
    echo "  - Run pipeline: python3 -m Summarizer.cli run --output-dir runs/test --max-articles 3"
    if [ ! -f "$MAIL_SCRIPT" ]; then
        echo "  - Setup Mail rule: ./setup-mail-rule.sh"
    fi
    echo ""
    exit 0
else
    echo -e "${RED}Some checks failed. Please fix the above issues.${NC}"
    echo ""
    echo "For help, see:"
    echo "  - SETUP.md (setup guide)"
    echo "  - README.md (quick start)"
    echo ""
    exit 1
fi
