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
log_info "Configuring AppleScript..."

# Replace {{EMAIL}} and {{REPO_PATH}} placeholders
sed -e "s|{{EMAIL}}|$USER_EMAIL|g" \
    -e "s|{{REPO_PATH}}|$REPO_ROOT|g" \
    "$TEMPLATE_FILE" > "$TARGET_FILE"

if [ -f "$TARGET_FILE" ]; then
    log_success "AppleScript installed: $TARGET_FILE"
    log_success "Configured for: $USER_EMAIL"
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
