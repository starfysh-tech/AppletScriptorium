#!/usr/bin/env bash
# commitcraft-setup.sh - Interactive setup and validation for CommitCraft tooling
# Usage: commitcraft-setup.sh [--check] [--section NAME]

set -euo pipefail

# Script metadata
SCRIPT_VERSION="2.0.0"
TEMPLATES_DIR="${HOME}/.claude/skills/commitcraft/templates"

# Color codes (only for interactive mode)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
DIM='\033[2m'
NC='\033[0m' # No Color

# Global state
STATE_commitlint=""
STATE_gitleaks=""
STATE_precommit_hooks=""
STATE_signed_commits=""
STATE_release_please=""
STATE_commitlint_ci=""
STATE_branch_protection=""
DETAIL_commitlint=""
DETAIL_gitleaks=""
DETAIL_precommit_hooks=""
DETAIL_signed_commits=""
DETAIL_release_please=""
DETAIL_commitlint_ci=""
DETAIL_branch_protection=""
declare -a ECOSYSTEMS
CHECK_MODE=false
SECTION_NAME=""
REPO_ROOT=""
REPO_PATH=""
HOOK_MANAGER=""

# ============================================================================
# Utility Functions
# ============================================================================

log_info() {
    if [[ "$CHECK_MODE" == "false" ]]; then
        echo -e "${BLUE}ℹ${NC} $*"
    fi
}

log_success() {
    if [[ "$CHECK_MODE" == "false" ]]; then
        echo -e "${GREEN}✓${NC} $*"
    fi
}

log_warn() {
    if [[ "$CHECK_MODE" == "false" ]]; then
        echo -e "${YELLOW}⚠${NC} $*"
    fi
}

log_error() {
    echo -e "${RED}✗${NC} $*" >&2
}

safe_timeout() {
    local timeout_seconds="$1"
    shift

    if command -v timeout &>/dev/null; then
        timeout "$timeout_seconds" "$@" 2>/dev/null || true
    elif command -v gtimeout &>/dev/null; then
        gtimeout "$timeout_seconds" "$@" 2>/dev/null || true
    else
        "$@" 2>/dev/null || true
    fi
}

ask_yes_no() {
    local prompt="$1"
    local default="${2:-n}"

    if [[ "$CHECK_MODE" == "true" ]]; then
        return 1
    fi

    local choice
    if [[ "$default" == "y" ]]; then
        read -rp "$prompt [Y/n] " choice
        choice="${choice:-y}"
    else
        read -rp "$prompt [y/N] " choice
        choice="${choice:-n}"
    fi

    [[ "$choice" =~ ^[Yy] ]]
}

# ============================================================================
# Argument Parsing
# ============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --check)
                CHECK_MODE=true
                shift
                ;;
            --section)
                SECTION_NAME="$2"
                shift 2
                ;;
            *)
                log_error "Unknown argument: $1"
                echo "Usage: $0 [--check] [--section NAME]"
                exit 1
                ;;
        esac
    done
}

# ============================================================================
# Environment Detection
# ============================================================================

detect_environment() {
    REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")

    if [[ -z "$REPO_ROOT" ]]; then
        log_error "Not in a git repository"
        exit 1
    fi

    cd "$REPO_ROOT" || exit 1

    ECOSYSTEMS=()

    # Detect Node
    if [[ -f "package.json" ]]; then
        ECOSYSTEMS+=("node")
    fi

    # Detect Python
    if [[ -f "pyproject.toml" ]] || [[ -f "setup.py" ]] || [[ -f "requirements.txt" ]]; then
        ECOSYSTEMS+=("python")
    fi

    # Detect Go
    if [[ -f "go.mod" ]]; then
        ECOSYSTEMS+=("go")
    fi

    # Fallback to generic
    if [[ ${#ECOSYSTEMS[@]} -eq 0 ]]; then
        ECOSYSTEMS=("generic")
    fi

    log_info "Detected ecosystems: ${ECOSYSTEMS[*]}"
}

# ============================================================================
# State Checking
# ============================================================================

check_commitlint() {
    local has_config=false
    local has_tool=false
    local config_file=""
    local extends_conventional=false
    local cli_version=""
    local detail_parts=()

    # Check for config files (expanded list)
    for file in "commitlint.config.js" ".commitlintrc.yml" ".commitlintrc.json" \
                ".commitlintrc.js" "commitlint.config.mjs" "commitlint.config.ts"; do
        if [[ -f "$file" ]]; then
            has_config=true
            config_file="$file"
            # Check if config extends config-conventional
            if grep -q "config-conventional" "$file" 2>/dev/null; then
                extends_conventional=true
            fi
            break
        fi
    done

    # Check package.json for commitlint key
    if [[ -f "package.json" ]] && grep -q '"commitlint"' package.json 2>/dev/null; then
        has_config=true
        if [[ -z "$config_file" ]]; then
            config_file="package.json"
        fi
        if grep -q "config-conventional" package.json 2>/dev/null; then
            extends_conventional=true
        fi
    fi

    # Check for tool (Node)
    if [[ " ${ECOSYSTEMS[*]} " =~ " node " ]]; then
        if grep -q "@commitlint/cli" package.json 2>/dev/null; then
            has_tool=true
            # Capture CLI version
            cli_version=$(safe_timeout 5 npx commitlint --version | head -n1)
        fi
    fi

    # Check for tool (Python)
    if [[ " ${ECOSYSTEMS[*]} " =~ " python " ]]; then
        if grep -q "\[tool.commitizen\]" pyproject.toml 2>/dev/null; then
            has_tool=true
        fi
    fi

    # Build detail string
    if [[ "$has_config" == "true" ]] && [[ "$has_tool" == "true" ]]; then
        STATE_commitlint="CONFIGURED"
        detail_parts+=("config: $config_file")
        if [[ "$extends_conventional" == "true" ]]; then
            detail_parts+=("(extends config-conventional)")
        fi
        if [[ -n "$cli_version" ]]; then
            detail_parts+=("@commitlint/cli $cli_version")
        fi
        DETAIL_commitlint="${detail_parts[*]}"
    elif [[ "$has_config" == "true" ]] || [[ "$has_tool" == "true" ]]; then
        STATE_commitlint="PARTIAL"
        if [[ "$has_config" == "true" ]]; then
            detail_parts+=("config: $config_file found")
        fi
        if [[ "$has_tool" == "false" ]]; then
            detail_parts+=("@commitlint/cli not in package.json")
        fi
        DETAIL_commitlint="${detail_parts[*]}"
    else
        STATE_commitlint="MISSING"
        DETAIL_commitlint="no config file found, @commitlint/cli not in package.json"
    fi
}

check_gitleaks() {
    local has_binary=false
    local has_config=false
    local gitleaks_version=""
    local hook_integration=false
    local has_ci_workflow=false
    local detail_parts=()

    if command -v gitleaks &>/dev/null; then
        has_binary=true
        # Capture version
        gitleaks_version=$(safe_timeout 5 gitleaks version | head -n1)
    fi

    if [[ -f ".gitleaks.toml" ]]; then
        has_config=true
    fi

    # Check hook integration
    if [[ -f ".husky/pre-commit" ]] && grep -q "gitleaks" ".husky/pre-commit" 2>/dev/null; then
        hook_integration=true
    fi
    if [[ -f ".pre-commit-config.yaml" ]] && grep -q "gitleaks" ".pre-commit-config.yaml" 2>/dev/null; then
        hook_integration=true
    fi

    # Check CI workflow
    if [[ -f ".github/workflows/gitleaks.yml" ]]; then
        has_ci_workflow=true
    fi

    # Build detail string
    if [[ "$has_binary" == "true" ]] && [[ "$has_config" == "true" ]]; then
        STATE_gitleaks="CONFIGURED"
        if [[ -n "$gitleaks_version" ]]; then
            detail_parts+=("gitleaks $gitleaks_version")
        fi
        detail_parts+=("config: .gitleaks.toml")
        if [[ "$hook_integration" == "true" ]]; then
            detail_parts+=("pre-commit hook")
        fi
        if [[ "$has_ci_workflow" == "true" ]]; then
            detail_parts+=("CI workflow")
        else
            detail_parts+=("no CI workflow")
        fi
        DETAIL_gitleaks="${detail_parts[*]}"
    elif [[ "$has_binary" == "true" ]] || [[ "$has_config" == "true" ]]; then
        STATE_gitleaks="PARTIAL"
        if [[ "$has_binary" == "true" ]]; then
            detail_parts+=("gitleaks binary found")
        fi
        if [[ "$has_config" == "false" ]]; then
            detail_parts+=("but no .gitleaks.toml config")
        fi
        DETAIL_gitleaks="${detail_parts[*]}"
    else
        STATE_gitleaks="MISSING"
        DETAIL_gitleaks="gitleaks binary not found, no .gitleaks.toml config"
    fi
}

check_precommit_hooks() {
    local status="MISSING"
    local detail_parts=()
    local hook_names=()
    local warnings=()

    # Check for husky - detect if ANY hook exists
    if [[ -d ".husky" ]]; then
        local husky_hooks=()
        for hook in commit-msg pre-commit pre-push; do
            if [[ -f ".husky/$hook" ]]; then
                husky_hooks+=("$hook")

                # Identify what each hook runs
                local hook_tool=""
                if grep -q "commitlint" ".husky/$hook" 2>/dev/null; then
                    hook_tool="commitlint"
                elif grep -q "gitleaks" ".husky/$hook" 2>/dev/null; then
                    hook_tool="gitleaks"
                fi

                if [[ -n "$hook_tool" ]]; then
                    hook_names+=("$hook ($hook_tool)")
                else
                    hook_names+=("$hook")
                fi

                # Check if hook is executable
                if [[ ! -x ".husky/$hook" ]]; then
                    warnings+=("not executable: $hook")
                fi
            fi
        done

        if [[ ${#husky_hooks[@]} -gt 0 ]]; then
            HOOK_MANAGER="husky"
            status="CONFIGURED"
            detail_parts+=("husky: ${hook_names[*]}")
        fi
    fi

    # Check for pre-commit framework
    if [[ -f ".pre-commit-config.yaml" ]] && [[ -f ".git/hooks/pre-commit" ]]; then
        HOOK_MANAGER="pre-commit"
        status="CONFIGURED"
        detail_parts+=("pre-commit framework")
    fi

    STATE_precommit_hooks="$status"

    # Build detail string
    if [[ "$status" == "CONFIGURED" ]]; then
        DETAIL_precommit_hooks="${detail_parts[*]}"
        if [[ ${#warnings[@]} -gt 0 ]]; then
            DETAIL_precommit_hooks="$DETAIL_precommit_hooks
    WARNING: ${warnings[*]}"
        fi
    else
        DETAIL_precommit_hooks="no pre-commit hooks detected"
    fi
}

check_signed_commits() {
    local status="MISSING"
    local detail_parts=()

    local gpgsign=$(git config --get commit.gpgsign 2>/dev/null || echo "")
    local gpg_format=$(git config --get gpg.format 2>/dev/null || echo "")
    local signing_key=$(git config --get user.signingkey 2>/dev/null || echo "")

    if [[ "$gpgsign" == "true" ]]; then
        # Check if signing key is configured
        if [[ -n "$signing_key" ]]; then
            status="CONFIGURED"
            detail_parts+=("gpgsign=true")
            if [[ -n "$gpg_format" ]]; then
                detail_parts+=("format=$gpg_format")
            fi
            detail_parts+=("key configured")
            DETAIL_signed_commits="${detail_parts[*]}"
        else
            status="PARTIAL"
            DETAIL_signed_commits="gpgsign=true but no signing key configured"
        fi
    else
        status="MISSING"
        DETAIL_signed_commits="gpgsign not enabled"
    fi

    STATE_signed_commits="$status"
}

check_release_please() {
    local status="MISSING"
    local has_workflow=false
    local has_config=false
    local has_manifest=false
    local release_type=""
    local version=""
    local missing_files=()

    # Check for workflow file
    if [[ -f ".github/workflows/release-please.yml" ]]; then
        has_workflow=true
    else
        missing_files+=("workflow")
    fi

    # Check for config and parse release-type
    if [[ -f "release-please-config.json" ]]; then
        has_config=true
        release_type=$(grep -o '"release-type"[[:space:]]*:[[:space:]]*"[^"]*"' release-please-config.json 2>/dev/null | cut -d'"' -f4 || echo "")
    else
        missing_files+=("config")
    fi

    # Check for manifest and parse version
    if [[ -f ".release-please-manifest.json" ]]; then
        has_manifest=true
        version=$(grep -o '"."[[:space:]]*:[[:space:]]*"[^"]*"' .release-please-manifest.json 2>/dev/null | head -n1 | cut -d'"' -f4 || echo "")
    else
        missing_files+=("manifest")
    fi

    # Determine status
    if [[ "$has_workflow" == "true" ]] && [[ "$has_config" == "true" ]] && [[ "$has_manifest" == "true" ]]; then
        status="CONFIGURED"
        DETAIL_release_please="type: ${release_type:-unknown}, version: ${version:-unknown}, workflow + config + manifest"
    elif [[ "$has_workflow" == "true" ]] || [[ "$has_config" == "true" ]] || [[ "$has_manifest" == "true" ]]; then
        status="PARTIAL"
        DETAIL_release_please="missing: ${missing_files[*]}"
    else
        DETAIL_release_please=""
    fi

    STATE_release_please="$status"
}

check_commitlint_ci() {
    local status="MISSING"
    local approach=""

    if [[ -f ".github/workflows/commitlint.yml" ]]; then
        status="CONFIGURED"
        # Detect which approach is used
        if grep -q "wagoid/commitlint-github-action" ".github/workflows/commitlint.yml" 2>/dev/null; then
            approach="wagoid/commitlint-github-action"
        elif grep -q "npx commitlint" ".github/workflows/commitlint.yml" 2>/dev/null; then
            approach="npx commitlint"
        else
            approach="unknown"
        fi
        DETAIL_commitlint_ci="workflow: commitlint.yml ($approach)"
    else
        DETAIL_commitlint_ci=""
    fi

    STATE_commitlint_ci="$status"
}

check_branch_protection() {
    local status="UNKNOWN"

    if ! command -v gh &>/dev/null; then
        STATE_branch_protection="UNKNOWN"
        DETAIL_branch_protection="gh CLI not available"
        return
    fi

    local remote_url=$(git config --get remote.origin.url 2>/dev/null || echo "")
    if [[ -z "$remote_url" ]]; then
        STATE_branch_protection="UNKNOWN"
        DETAIL_branch_protection="no GitHub remote found"
        return
    fi

    # Extract owner/repo from URL and store globally
    REPO_PATH=$(echo "$remote_url" | sed -E 's#.*github\.com[:/]##' | sed 's/\.git$//')

    local api_response
    api_response=$(gh api "repos/$REPO_PATH/branches/main/protection" 2>/dev/null || echo "")

    if [[ -n "$api_response" ]]; then
        status="CONFIGURED"

        # Parse API response for details
        local pr_reviews=""
        local status_checks=""
        local signed_commits=""
        local linear_history=""

        if command -v jq &>/dev/null; then
            pr_reviews=$(echo "$api_response" | jq -r '.required_pull_request_reviews.required_approving_review_count // 0' 2>/dev/null || echo "")
            status_checks=$(echo "$api_response" | jq -r '.required_status_checks.contexts[]? // empty' 2>/dev/null | tr '\n' ', ' | sed 's/,$//' || echo "")
            signed_commits=$(echo "$api_response" | jq -r '.required_signatures.enabled // false' 2>/dev/null || echo "")
            linear_history=$(echo "$api_response" | jq -r '.required_linear_history.enabled // false' 2>/dev/null || echo "")
        else
            # Grep fallback
            pr_reviews=$(echo "$api_response" | grep -o '"required_approving_review_count"[[:space:]]*:[[:space:]]*[0-9]*' | grep -o '[0-9]*' || echo "0")
            signed_commits=$(echo "$api_response" | grep -q '"required_signatures"' && echo "true" || echo "false")
            linear_history=$(echo "$api_response" | grep -q '"required_linear_history"' && echo "true" || echo "false")
        fi

        # Build detail string
        local detail_parts=()
        if [[ -n "$pr_reviews" ]]; then
            detail_parts+=("PR reviews: $pr_reviews required")
        fi
        if [[ -n "$status_checks" ]]; then
            detail_parts+=("status checks: $status_checks")
        fi
        if [[ "$signed_commits" == "true" ]]; then
            detail_parts+=("signed commits: yes")
        fi
        if [[ "$linear_history" == "true" ]]; then
            detail_parts+=("linear history: yes")
        fi

        if [[ ${#detail_parts[@]} -gt 0 ]]; then
            DETAIL_branch_protection="${detail_parts[*]}"
        else
            DETAIL_branch_protection="configured (details unavailable)"
        fi
    else
        status="MISSING"
        DETAIL_branch_protection="not configured -> https://github.com/$REPO_PATH/settings/branches"
    fi

    STATE_branch_protection="$status"
}

check_existing_setup() {
    check_commitlint
    check_gitleaks
    check_precommit_hooks
    check_signed_commits
    check_release_please
    check_commitlint_ci
    check_branch_protection
}

# ============================================================================
# Check Mode Output
# ============================================================================

print_report() {
    echo ""
    echo -e "${BLUE}CommitCraft${NC} — Configuration Report"
    echo "Repository: $REPO_ROOT"
    echo "Ecosystems: ${ECOSYSTEMS[*]}"
    echo ""

    # Readable names and action hints for each component
    local -a keys=(commitlint gitleaks precommit_hooks signed_commits release_please commitlint_ci branch_protection)
    local -a names=("Conventional Commits" "Secret Scanning" "Pre-commit Hooks" "Signed Commits" "Release Automation" "Commitlint CI" "Branch Protection")
    local -a hints=(
        "Run: /commitcraft setup --section commitlint"
        "Run: /commitcraft setup --section gitleaks"
        "Run: /commitcraft setup --section precommit"
        "Run: /commitcraft setup --section signing"
        "Run: /commitcraft setup --section release"
        "Run: /commitcraft setup --section ci"
        "Configure in GitHub repo settings"
    )

    printf "  %-25s %s\n" "Component" "Status"
    printf "  %-25s %s\n" "─────────────────────────" "──────────────"

    local configured_count=0
    local total=${#keys[@]}
    local i

    for ((i=0; i<total; i++)); do
        local var="STATE_${keys[$i]}"
        local detail_var="DETAIL_${keys[$i]}"
        local status="${!var}"
        local detail="${!detail_var}"
        local icon color hint_text=""

        case "$status" in
            CONFIGURED) icon="✓"; color="$GREEN"; configured_count=$((configured_count + 1)) ;;
            PARTIAL)    icon="◑"; color="$YELLOW"; hint_text="  ${hints[$i]}" ;;
            MISSING)    icon="✗"; color="$RED";    hint_text="  ${hints[$i]}" ;;
            UNKNOWN)    icon="?"; color="$BLUE" ;;
        esac

        # Print status row
        printf "  %-25s ${color}%s %s${NC}%s\n" "${names[$i]}" "$icon" "$status" "$hint_text"

        # Print detail row if available
        if [[ -n "$detail" ]]; then
            case "$status" in
                CONFIGURED)
                    # CONFIGURED: dim color, indented, no prefix
                    echo -e "    ${DIM}${detail}${NC}"
                    ;;
                MISSING|PARTIAL)
                    # MISSING/PARTIAL: indented with -> prefix
                    echo "    -> $detail"
                    ;;
                UNKNOWN)
                    # UNKNOWN: indented, plain
                    echo "    $detail"
                    ;;
            esac
        fi
    done

    echo ""
    echo -e "  ${configured_count}/${total} configured"
    echo ""

    # Machine-parseable block (consumed by SKILL.md)
    echo "COMMITCRAFT_CHECK_START"
    for ((i=0; i<total; i++)); do
        local var="STATE_${keys[$i]}"
        local detail_var="DETAIL_${keys[$i]}"
        local detail="${!detail_var}"
        if [[ -n "$detail" ]]; then
            echo "${keys[$i]}: ${!var} | $detail"
        else
            echo "${keys[$i]}: ${!var}"
        fi
    done
    echo "COMMITCRAFT_CHECK_END"

    # Exit code: 0 if all configured, 1 if any missing/partial
    local exit_code=0
    for component in commitlint gitleaks precommit_hooks signed_commits release_please commitlint_ci; do
        local var="STATE_${component}"
        if [[ "${!var}" != "CONFIGURED" ]]; then
            exit_code=1
        fi
    done

    exit $exit_code
}

# ============================================================================
# Current State Display
# ============================================================================

show_current_state() {
    echo ""
    echo "=========================================="
    echo "  CommitCraft Setup - Current State"
    echo "=========================================="
    echo ""
    echo "Repository: $REPO_ROOT"
    echo "Ecosystems: ${ECOSYSTEMS[*]}"
    echo ""

    printf "%-25s %s\n" "Component" "Status"
    printf "%-25s %s\n" "-------------------------" "-------------"

    for component in commitlint gitleaks precommit_hooks signed_commits release_please commitlint_ci branch_protection; do
        local var="STATE_${component}"
        local status="${!var}"
        local color="$NC"

        case "$status" in
            CONFIGURED) color="$GREEN" ;;
            PARTIAL) color="$YELLOW" ;;
            MISSING) color="$RED" ;;
            UNKNOWN) color="$BLUE" ;;
        esac

        printf "%-25s ${color}%s${NC}\n" "$component" "$status"
    done

    echo ""
}

# ============================================================================
# Section 1: Conventional Commits (commitlint)
# ============================================================================

setup_commitlint() {
    echo ""
    echo "=========================================="
    echo "  Section 1: Conventional Commits"
    echo "=========================================="
    echo ""

    if [[ "${STATE_commitlint}" == "CONFIGURED" ]]; then
        log_success "commitlint already configured"
        return
    fi

    if ! ask_yes_no "Set up commitlint for conventional commits?" "y"; then
        log_info "Skipping commitlint setup"
        return
    fi

    if [[ " ${ECOSYSTEMS[*]} " =~ " node " ]]; then
        log_info "Installing commitlint for Node ecosystem..."
        npm install --save-dev @commitlint/cli @commitlint/config-conventional

        cp "$TEMPLATES_DIR/commitlint.config.js" "$REPO_ROOT/"
        log_success "Created commitlint.config.js"

        # Set up husky commit-msg hook
        if ! grep -q "husky" package.json 2>/dev/null; then
            npm install --save-dev husky
            npx husky init
        fi

        echo 'npx --no -- commitlint --edit "$1"' > .husky/commit-msg
        chmod +x .husky/commit-msg
        log_success "Created husky commit-msg hook"

        HOOK_MANAGER="husky"

    elif [[ " ${ECOSYSTEMS[*]} " =~ " python " ]]; then
        log_info "Installing commitizen for Python ecosystem..."

        if command -v pip &>/dev/null; then
            pip install commitizen
        elif command -v pip3 &>/dev/null; then
            pip3 install commitizen
        else
            log_error "pip not found - please install commitizen manually"
            return
        fi

        cp "$TEMPLATES_DIR/.commitlintrc.yml" "$REPO_ROOT/"
        log_success "Created .commitlintrc.yml"

    else
        log_info "Generic ecosystem - setting up config file only..."
        cp "$TEMPLATES_DIR/.commitlintrc.yml" "$REPO_ROOT/"
        log_success "Created .commitlintrc.yml"
        log_warn "Enforcement will be via CI only (no local hooks)"
    fi

    STATE_commitlint="CONFIGURED"
}

# ============================================================================
# Section 2: Security Scanning (gitleaks)
# ============================================================================

_setup_gitleaks_ci_workflow() {
    mkdir -p .github/workflows
    cp "$TEMPLATES_DIR/gitleaks.yml" "$REPO_ROOT/.github/workflows/gitleaks.yml"
    log_success "Created .github/workflows/gitleaks.yml"

    # Detect org vs personal to give accurate secret instructions
    local owner_type=""
    if command -v gh &>/dev/null; then
        owner_type=$(gh repo view --json owner --jq '.owner.type' 2>/dev/null || echo "")
    fi

    if [[ "$owner_type" == "Organization" ]]; then
        log_warn "Organization repo: GITLEAKS_LICENSE secret required"
        echo "  → Settings → Secrets and variables → Actions → New organization secret"
        echo "  → Name: GITLEAKS_LICENSE"
        echo "  → Get license: https://gitleaks.io"
    else
        log_info "Personal repo: GITLEAKS_LICENSE not required"
    fi
}

setup_gitleaks() {
    echo ""
    echo "=========================================="
    echo "  Section 2: Security Scanning (gitleaks)"
    echo "=========================================="
    echo ""

    if [[ "${STATE_gitleaks}" == "CONFIGURED" ]]; then
        # Local scanning configured — check if CI workflow is also present
        if [[ -f ".github/workflows/gitleaks.yml" ]]; then
            log_success "gitleaks already configured"
            return
        fi
        log_success "gitleaks local scanning configured"
        if ask_yes_no "Set up gitleaks GitHub Actions CI workflow?" "y"; then
            _setup_gitleaks_ci_workflow
        fi
        return
    fi

    if ! ask_yes_no "Set up gitleaks for secret scanning?" "y"; then
        log_info "Skipping gitleaks setup"
        return
    fi

    # Check if gitleaks is installed
    if ! command -v gitleaks &>/dev/null; then
        log_warn "gitleaks not found"

        if command -v brew &>/dev/null; then
            if ask_yes_no "Install gitleaks via Homebrew?" "y"; then
                brew install gitleaks
            fi
        elif command -v go &>/dev/null; then
            if ask_yes_no "Install gitleaks via Go?" "y"; then
                go install github.com/gitleaks/gitleaks/v8@latest
            fi
        else
            log_error "Please install gitleaks manually: https://github.com/gitleaks/gitleaks"
            return
        fi
    fi

    # Copy config
    cp "$TEMPLATES_DIR/.gitleaks.toml" "$REPO_ROOT/"
    log_success "Created .gitleaks.toml"

    # Add to pre-commit hook
    if [[ "$HOOK_MANAGER" == "husky" ]]; then
        if [[ ! -f ".husky/pre-commit" ]]; then
            echo '#!/usr/bin/env sh' > .husky/pre-commit
            echo '. "$(dirname -- "$0")/_/husky.sh"' >> .husky/pre-commit
        fi
        echo 'gitleaks protect --staged --verbose' >> .husky/pre-commit
        chmod +x .husky/pre-commit
        log_success "Added gitleaks to husky pre-commit hook"
    fi

    # Create GitHub Actions CI workflow
    _setup_gitleaks_ci_workflow

    log_info "Recommendation: Enable GitHub push protection in repo settings"

    STATE_gitleaks="CONFIGURED"
}

# ============================================================================
# Section 3: Pre-commit Hooks
# ============================================================================

setup_precommit_hooks() {
    echo ""
    echo "=========================================="
    echo "  Section 3: Pre-commit Hook Manager"
    echo "=========================================="
    echo ""

    if [[ "${STATE_precommit_hooks}" == "CONFIGURED" ]]; then
        log_success "Pre-commit hooks already configured (manager: $HOOK_MANAGER)"
        return
    fi

    # If multi-ecosystem, ask which manager to use
    if [[ ${#ECOSYSTEMS[@]} -gt 1 ]]; then
        log_info "Multi-ecosystem repo detected"
        echo "Which hook manager do you prefer?"
        echo "1) husky (Node-centric)"
        echo "2) pre-commit framework (Python-centric, language-agnostic)"
        read -rp "Choice [1]: " choice
        choice="${choice:-1}"

        if [[ "$choice" == "2" ]]; then
            HOOK_MANAGER="pre-commit"
        else
            HOOK_MANAGER="husky"
        fi
    elif [[ " ${ECOSYSTEMS[*]} " =~ " node " ]]; then
        HOOK_MANAGER="husky"
    else
        HOOK_MANAGER="pre-commit"
    fi

    if [[ "$HOOK_MANAGER" == "husky" ]]; then
        if ! grep -q "husky" package.json 2>/dev/null; then
            log_info "Installing husky..."
            npm install --save-dev husky
            npx husky init
        fi
        log_success "Husky configured"

    elif [[ "$HOOK_MANAGER" == "pre-commit" ]]; then
        if ! command -v pre-commit &>/dev/null; then
            log_info "Installing pre-commit framework..."
            if command -v pip &>/dev/null; then
                pip install pre-commit
            elif command -v pip3 &>/dev/null; then
                pip3 install pre-commit
            elif command -v brew &>/dev/null; then
                brew install pre-commit
            else
                log_error "Could not install pre-commit - please install manually"
                return
            fi
        fi

        cp "$TEMPLATES_DIR/.pre-commit-config.yaml" "$REPO_ROOT/"
        log_success "Created .pre-commit-config.yaml"

        pre-commit install
        log_success "Installed pre-commit hooks"
    fi

    STATE_precommit_hooks="CONFIGURED"
}

# ============================================================================
# Section 4: Signed Commits
# ============================================================================

setup_signed_commits() {
    echo ""
    echo "=========================================="
    echo "  Section 4: Signed Commits"
    echo "=========================================="
    echo ""

    if [[ "${STATE_signed_commits}" == "CONFIGURED" ]]; then
        log_success "Signed commits already configured"
        return
    fi

    if ! ask_yes_no "Set up commit signing?" "y"; then
        log_info "Skipping signed commits setup"
        return
    fi

    # Detect existing keys
    local has_ssh_keys=false
    local has_gpg_keys=false

    if ls ~/.ssh/*.pub &>/dev/null; then
        has_ssh_keys=true
    fi

    if gpg --list-secret-keys &>/dev/null | grep -q "sec"; then
        has_gpg_keys=true
    fi

    log_info "Detected keys: SSH=$has_ssh_keys, GPG=$has_gpg_keys"

    echo ""
    echo "Choose signing method:"
    echo "1) SSH signing (simpler, recommended)"
    echo "2) GPG signing (traditional)"
    read -rp "Choice [1]: " choice
    choice="${choice:-1}"

    if [[ "$choice" == "1" ]]; then
        # SSH signing
        local ssh_key
        if [[ "$has_ssh_keys" == "true" ]]; then
            ssh_key=$(ls ~/.ssh/*.pub | head -n1)
            log_info "Using SSH key: $ssh_key"
        else
            log_info "Generating new SSH key..."
            ssh-keygen -t ed25519 -C "$(git config user.email)"
            ssh_key="${HOME}/.ssh/id_ed25519.pub"
        fi

        git config commit.gpgsign true
        git config gpg.format ssh
        git config user.signingkey "$ssh_key"

        log_success "SSH signing configured"
        log_info "Add your public key to GitHub: https://github.com/settings/keys"

    else
        # GPG signing
        if [[ "$has_gpg_keys" == "false" ]]; then
            log_info "No GPG keys found. Generate one with: gpg --full-generate-key"
            log_info "Then configure with: git config user.signingkey <KEY_ID>"
            return
        fi

        local key_id
        key_id=$(gpg --list-secret-keys --keyid-format=long | grep "sec" | head -n1 | awk '{print $2}' | cut -d'/' -f2)

        git config commit.gpgsign true
        git config user.signingkey "$key_id"

        log_success "GPG signing configured with key: $key_id"
        log_info "Add your GPG key to GitHub: https://github.com/settings/keys"
    fi

    STATE_signed_commits="CONFIGURED"
}

# ============================================================================
# Section 5: Release Automation (release-please)
# ============================================================================

setup_release_please() {
    echo ""
    echo "=========================================="
    echo "  Section 5: Release Automation"
    echo "=========================================="
    echo ""

    if [[ "${STATE_release_please}" == "CONFIGURED" ]]; then
        log_success "release-please already configured"
        return
    fi

    if ! ask_yes_no "Set up release-please for automated releases?" "y"; then
        log_info "Skipping release-please setup"
        return
    fi

    # Auto-detect release type
    local release_type="simple"

    if [[ " ${ECOSYSTEMS[*]} " =~ " node " ]]; then
        release_type="node"
    elif [[ " ${ECOSYSTEMS[*]} " =~ " python " ]]; then
        release_type="python"
    elif [[ " ${ECOSYSTEMS[*]} " =~ " go " ]]; then
        release_type="go"
    fi

    echo "Detected release type: $release_type"
    read -rp "Press Enter to use '$release_type', or enter type [node/python/go/simple]: " user_type

    # Validate release type input
    if [[ -n "$user_type" ]]; then
        case "$user_type" in
            node|python|go|simple)
                release_type="$user_type"
                ;;
            *)
                log_warn "Invalid release type '$user_type' — using detected default '$release_type'"
                ;;
        esac
    fi

    # Ask for initial version
    read -rp "Initial version [0.0.0]: " initial_version

    # Validate version input (basic semver pattern: N.N.N)
    if [[ -n "$initial_version" ]]; then
        if [[ ! "$initial_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            log_warn "Invalid version '$initial_version' — using default '0.0.0'"
            initial_version="0.0.0"
        fi
    else
        initial_version="0.0.0"
    fi

    # Create GitHub Actions workflow directory
    mkdir -p .github/workflows

    # Copy workflow file
    cp "$TEMPLATES_DIR/release-please.yml" "$REPO_ROOT/.github/workflows/"
    log_success "Created .github/workflows/release-please.yml"

    # Create config file
    sed "s/RELEASE_TYPE_PLACEHOLDER/$release_type/" "$TEMPLATES_DIR/release-please-config.json" > "$REPO_ROOT/release-please-config.json"
    log_success "Created release-please-config.json"

    # Create manifest file
    echo "{" > .release-please-manifest.json
    echo "  \".\": \"$initial_version\"" >> .release-please-manifest.json
    echo "}" >> .release-please-manifest.json
    log_success "Created .release-please-manifest.json"

    STATE_release_please="CONFIGURED"
}

# ============================================================================
# Section 6: GitHub Actions CI
# ============================================================================

setup_ci_workflows() {
    echo ""
    echo "=========================================="
    echo "  Section 6: GitHub Actions CI"
    echo "=========================================="
    echo ""

    if [[ "${STATE_commitlint_ci}" == "CONFIGURED" ]]; then
        log_success "commitlint CI already configured"
        return
    fi

    if ! ask_yes_no "Set up commitlint CI workflow?" "y"; then
        log_info "Skipping CI setup"
        return
    fi

    mkdir -p .github/workflows

    cp "$TEMPLATES_DIR/commitlint-ci.yml" "$REPO_ROOT/.github/workflows/commitlint.yml"
    log_success "Created .github/workflows/commitlint.yml"

    STATE_commitlint_ci="CONFIGURED"
}

# ============================================================================
# Section 7: Branch Protection Recommendations
# ============================================================================

recommend_branch_protection() {
    echo ""
    echo "=========================================="
    echo "  Section 7: Branch Protection"
    echo "=========================================="
    echo ""

    if [[ "${STATE_branch_protection}" == "UNKNOWN" ]]; then
        log_warn "Cannot check branch protection (gh CLI not available or no remote)"
        return
    fi

    if [[ "${STATE_branch_protection}" == "CONFIGURED" ]]; then
        log_success "Branch protection already configured"
        return
    fi

    # Extract repo path for dynamic URL
    local remote_url=$(git config --get remote.origin.url 2>/dev/null || echo "")
    local repo_path=""
    if [[ -n "$remote_url" ]]; then
        repo_path=$(echo "$remote_url" | sed -E 's#.*github\.com[:/]##' | sed 's/\.git$//')
    fi

    echo "Recommended settings (Settings > Branches):"
    echo "  - Require pull request reviews (min 1)"
    echo "  - Require status checks to pass before merging (strict mode)"
    echo "    → Add required checks: commitlint, tests"
    echo "  - Require conversation resolution before merging"
    echo "  - Require signed commits"
    echo "  - Require linear history (squash or rebase only)"
    echo "  - Block force pushes and branch deletions"
    echo ""
    echo "Rulesets (Settings > Rules) — modern alternative:"
    echo "  - Layer multiple rulesets (branch protection only allows one match)"
    echo "  - Disable/enable without deleting"
    echo "  - Visible to all readers (not just admins)"
    echo "  - Push rules: file path, file size, extension restrictions"
    echo "  - Bypass permissions for specific roles/teams"
    echo ""

    if [[ -n "$repo_path" ]]; then
        log_info "Branch protection: https://github.com/$repo_path/settings/branches"
        log_info "Rulesets (modern): https://github.com/$repo_path/settings/rules"
    else
        log_warn "No GitHub remote found — configure manually:"
        log_info "  Branch protection: https://github.com/{owner}/{repo}/settings/branches"
        log_info "  Rulesets (modern): https://github.com/{owner}/{repo}/settings/rules"
    fi

    log_warn "Automatic configuration via API not yet implemented"
}

# ============================================================================
# Summary and Config Write
# ============================================================================

print_summary() {
    echo ""
    echo "=========================================="
    echo "  Setup Complete"
    echo "=========================================="
    echo ""

    log_success "CommitCraft v$SCRIPT_VERSION setup finished"
    echo ""

    printf "%-25s %s\n" "Component" "Status"
    printf "%-25s %s\n" "-------------------------" "-------------"

    for component in commitlint gitleaks precommit_hooks signed_commits release_please commitlint_ci branch_protection; do
        local var="STATE_${component}"
        local status="${!var}"
        local color="$NC"

        case "$status" in
            CONFIGURED) color="$GREEN" ;;
            PARTIAL) color="$YELLOW" ;;
            MISSING) color="$RED" ;;
            UNKNOWN) color="$BLUE" ;;
        esac

        printf "%-25s ${color}%s${NC}\n" "$component" "$status"
    done

    echo ""
    log_info "Run 'commitcraft-setup.sh --check' to validate configuration"
}

write_commitcraft_config() {
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    cat > "$REPO_ROOT/.commitcraft.json" <<EOF
{
  "version": "$SCRIPT_VERSION",
  "configured_at": "$timestamp",
  "ecosystems": [$(printf '"%s",' "${ECOSYSTEMS[@]}" | sed 's/,$//')],
  "hook_manager": "$HOOK_MANAGER",
  "components": {
    "commitlint": "${STATE_commitlint}",
    "gitleaks": "${STATE_gitleaks}",
    "precommit_hooks": "${STATE_precommit_hooks}",
    "signed_commits": "${STATE_signed_commits}",
    "release_please": "${STATE_release_please}",
    "commitlint_ci": "${STATE_commitlint_ci}",
    "branch_protection": "${STATE_branch_protection}"
  }
}
EOF

    log_success "Written .commitcraft.json"
}

# ============================================================================
# Main
# ============================================================================

main() {
    parse_args "$@"
    detect_environment
    check_existing_setup

    if [[ "$CHECK_MODE" == "true" ]]; then
        print_report
        exit 0
    fi

    show_current_state

    # Run specific section or all sections
    if [[ -n "$SECTION_NAME" ]]; then
        case "$SECTION_NAME" in
            commitlint) setup_commitlint ;;
            gitleaks) setup_gitleaks ;;
            precommit|hooks) setup_precommit_hooks ;;
            signing) setup_signed_commits ;;
            release) setup_release_please ;;
            ci) setup_ci_workflows ;;
            branch-protection) recommend_branch_protection ;;
            *)
                log_error "Unknown section: $SECTION_NAME"
                exit 1
                ;;
        esac
    else
        setup_commitlint
        setup_gitleaks
        setup_precommit_hooks
        setup_signed_commits
        setup_release_please
        setup_ci_workflows
        recommend_branch_protection
    fi

    print_summary
    write_commitcraft_config
}

main "$@"
