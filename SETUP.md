# AppletScriptorium Setup Guide

Complete instructions for setting up AppletScriptorium on a new macOS computer.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation Steps](#installation-steps)
- [Configuration](#configuration)
- [Verification](#verification)
- [First Run](#first-run)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements
- **macOS**: 12.0 (Monterey) or later (tested on macOS 15.6.1)
- **Python**: 3.11 or later
- **Mail.app**: Configured with at least one email account
- **Disk Space**: ~2GB for dependencies and models

### Required Tools
1. **Homebrew** (package manager)
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Python 3.11+**
   ```bash
   brew install python@3.11
   ```

3. **Ollama** (local LLM runtime)
   ```bash
   brew install ollama
   ```

4. **Git** (likely already installed)
   ```bash
   git --version  # Verify installation
   ```

### Optional Tools
- **jq** (for JSON inspection): `brew install jq`
- **pytest** (for running tests): Included in requirements.txt

---

## Installation Steps

### 1. Clone Repository
```bash
cd ~/Code  # Or your preferred project directory
git clone https://github.com/yourusername/AppletScriptorium.git
cd AppletScriptorium
```

### 2. Install Python Dependencies

#### Option A: System Python (for Mail rule automation)
```bash
python3 -m pip install --user -r Summarizer/requirements.txt
```

**Required packages:**
- beautifulsoup4
- pytest
- httpx
- readability-lxml
- markdownify
- crawlee
- browserforge
- apify_fingerprint_datapoints

#### Option B: Virtual Environment (for development/testing)
```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r Summarizer/requirements.txt
```

**Note:** Mail rule automation requires system Python at `/usr/local/bin/python3`. Virtual environments won't work with Mail rules.

### 3. Install Playwright (for Cloudflare-protected sites)
```bash
# With system Python
python3 -m playwright install

# With virtual environment (after activating)
python3 -m playwright install
```

This downloads Chromium browsers needed for headless fetching (~200MB).

### 4. Install Ollama Model
```bash
# Start Ollama service (required before pulling models)
brew services start ollama

# Pull the granite4:tiny-h model (~1GB)
ollama pull granite4:tiny-h

# Verify installation
ollama list | grep granite4
```

**Alternative models:**
```bash
# For experimentation (adjust --model flag in CLI)
ollama pull qwen3:latest
ollama pull llama3:latest
```

### 5. Verify File Permissions
```bash
# Make AppleScript executable (if needed)
chmod +x Summarizer/fetch-alert-source.applescript

# Make shell scripts executable
chmod +x run_workflow.sh
chmod +x Summarizer/bin/run_pro_alert.sh
```

### 6. Create Required Directories
```bash
# Create output directory for pipeline runs
mkdir -p runs

# Verify structure
ls -la
# Should show: CLAUDE.md, README.md, Summarizer/, runs/, etc.
```

---

## Configuration

### Mail.app Setup (for automation)

#### For Mail Rule Automation (Recommended)
See detailed instructions in: `Summarizer/MAIL_RULE_SETUP.md`

Quick steps:
1. Copy AppleScript to Mail's script directory:
   ```bash
   mkdir -p ~/Library/Application\ Scripts/com.apple.mail/
   # You'll need to create process-pro-alert.scpt manually or from template
   ```

2. Configure Mail rule in Mail.app:
   - **From**: `googlealerts-noreply@google.com`
   - **Subject**: `Google Alert -`
   - **Action**: Run AppleScript → `process-pro-alert.scpt`

3. Grant permissions:
   - **System Settings** → **Privacy & Security** → **Accessibility**
   - Add Mail.app and enable

#### For Cron Automation (Alternative)
1. Create environment file:
   ```bash
   cat > ~/.pro-alert-env << 'ENVEOF'
   # PRO Alert Summarizer Configuration
   export PRO_ALERT_OUTPUT_DIR="$HOME/Code/AppletScriptorium/runs"
   export PRO_ALERT_MODEL="granite4:tiny-h"
   export PRO_ALERT_MAX_ARTICLES=""  # Empty = process all
   export PRO_ALERT_DIGEST_EMAIL="your-email@example.com"
   export PRO_ALERT_EMAIL_SENDER="your-email@example.com"
   export PRO_ALERT_EMAIL_RECIPIENT="your-email@example.com"  # For error notifications
   export PRO_ALERT_NOTIFY_ON_SUCCESS="0"  # Set to 1 for success notifications
   ENVEOF
   ```

2. Edit crontab:
   ```bash
   crontab -e
   ```

3. Add cron entry (weekdays at 7 AM):
   ```cron
   0 7 * * 1-5 /bin/bash -lc 'source ~/.pro-alert-env; /Users/YOUR_USERNAME/Code/AppletScriptorium/Summarizer/bin/run_pro_alert.sh'
   ```

   **Replace `YOUR_USERNAME`** with your actual macOS username.

### Environment Variables (Optional)

Add to `~/.zshrc` or `~/.bash_profile` for CLI usage:

```bash
# PRO Alert Summarizer defaults
export PRO_ALERT_MODEL="granite4:tiny-h"
export PRO_ALERT_DIGEST_EMAIL="your-email@example.com"
export PRO_ALERT_EMAIL_SENDER="your-email@example.com"

# Custom HTTP headers (for sites requiring authentication)
export PRO_ALERT_HTTP_HEADERS_JSON='{"example.com": {"Cookie": "session=abc"}}'
```

Reload shell:
```bash
source ~/.zshrc  # or ~/.bash_profile
```

---

## Verification

### 1. Verify Python Installation
```bash
which python3
# Should show: /usr/local/bin/python3 or /opt/homebrew/bin/python3

python3 --version
# Should show: Python 3.11.x or higher
```

### 2. Verify Python Packages
```bash
python3 -m pip list | grep -E "beautifulsoup4|httpx|readability|crawlee"
```

Expected output:
```
beautifulsoup4       4.13.4
httpx                0.27.x
readability-lxml     0.8.x
crawlee              1.0.x
```

### 3. Verify Ollama
```bash
# Check if Ollama service is running
brew services list | grep ollama
# Should show: ollama started

# List installed models
ollama list
# Should show: granite4:tiny-h

# Test model (optional)
echo "Summarize: Patient outcomes improve with new treatment" | ollama run granite4:tiny-h
```

### 4. Verify Playwright
```bash
python3 -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"
# Should print: Playwright OK
```

### 5. Run Tests
```bash
cd /Users/YOUR_USERNAME/Code/AppletScriptorium

# Run all tests
python3 -m pytest Summarizer/tests -v

# Expected: All tests pass (may show warnings)
```

---

## First Run

### Test with Sample Fixture
```bash
cd /Users/YOUR_USERNAME/Code/AppletScriptorium

# Parse sample alert (no network calls)
python3 Summarizer/clean-alert.py \
  Summarizer/Samples/google-alert-sample-2025-10-06.eml | head

# Should output TSV with article links
```

### Manual CLI Run (requires Google Alert in Mail.app inbox)
```bash
# Process most recent inbox message
python3 -m Summarizer.cli run \
  --output-dir runs/test-$(date +%Y%m%d-%H%M%S) \
  --max-articles 3 \
  --subject-filter "Google Alert -"

# Check outputs
ls -la runs/test-*/
# Should contain: alert.eml, alert.tsv, articles/, digest.html, digest.txt, workflow.log
```

### View Generated Digest
```bash
# Open HTML digest in browser
open runs/test-*/digest.html

# View plaintext digest
cat runs/test-*/digest.txt
```

### Send Test Email
```bash
python3 -m Summarizer.cli run \
  --output-dir runs/email-test-$(date +%Y%m%d-%H%M%S) \
  --max-articles 2 \
  --email-digest your-email@example.com \
  --email-sender your-email@example.com \
  --subject-filter "Google Alert -"

# Check Mail.app Sent folder for digest email
```

---

## Troubleshooting

### Python Dependencies Fail to Install

**Issue**: `pip install` fails with compilation errors

**Solutions**:
```bash
# Update pip and setuptools
python3 -m pip install --upgrade pip setuptools wheel

# Install Xcode Command Line Tools (if missing)
xcode-select --install

# Retry installation
python3 -m pip install -r Summarizer/requirements.txt
```

### Ollama Model Not Found

**Issue**: `ollama list` doesn't show granite4:tiny-h

**Solutions**:
```bash
# Start Ollama service
brew services start ollama

# Wait 5 seconds, then pull model
ollama pull granite4:tiny-h

# If pull hangs, check network connection and retry
```

### AppleScript Fails to Capture Email

**Issue**: "No messages found in inbox"

**Solutions**:
1. Verify Mail.app is running and has messages in Inbox
2. Check subject filter matches actual email subjects:
   ```bash
   # Remove subject filter to capture any inbox message
   python3 -m Summarizer.cli run --output-dir runs/test
   ```
3. Check Mail.app permissions:
   - **System Settings** → **Privacy & Security** → **Automation**
   - Enable Terminal → Mail

### Playwright Browser Not Found

**Issue**: "Executable doesn't exist at ..."

**Solutions**:
```bash
# Reinstall browsers
python3 -m playwright install --force

# If using virtual environment, activate first:
source .venv/bin/activate
python3 -m playwright install
```

### Article Fetching Fails

**Issue**: "Failed to fetch {url}"

**Solutions**:
1. Check network connection
2. For sites requiring authentication, set custom headers:
   ```bash
   export PRO_ALERT_HTTP_HEADERS_JSON='{"example.com": {"Cookie": "session=abc"}}'
   ```
3. Verify Playwright is installed (for Cloudflare-protected sites)
4. Increase timeout in `Summarizer/article_fetcher.py` (if needed)

### Tests Fail

**Issue**: `pytest` shows failures

**Solutions**:
```bash
# Run with verbose output
python3 -m pytest Summarizer/tests -v -s

# Run specific test file
python3 -m pytest Summarizer/tests/test_link_extractor.py -v

# Check if fixtures are outdated (rebuild)
Summarizer/refresh-fixtures.py
```

### Mail Rule Not Triggering

**Issue**: Mail rule doesn't execute automatically

**Solutions**:
1. Verify Mail rule conditions match incoming emails exactly
2. Check AppleScript exists:
   ```bash
   ls -la ~/Library/Application\ Scripts/com.apple.mail/process-pro-alert.scpt
   ```
3. Test rule manually:
   - Select a Google Alert email in Mail.app
   - **Message** menu → **Apply Rules**
4. Check Console.app for error messages:
   - Open Console.app → Search for "Mail" → Look for script errors

### Digest Email Not Sending

**Issue**: digest.eml created but email not sent

**Solutions**:
1. Verify Accessibility permissions (see MAIL_RULE_SETUP.md)
2. Increase delays in process-pro-alert.scpt
3. Test manually:
   ```bash
   open runs/*/digest.eml
   # Verify HTML renders in Mail.app viewer
   ```

---

## New Machine Checklist

Use this checklist when setting up on a fresh macOS installation:

- [ ] Install Homebrew
- [ ] Install Python 3.11+ via Homebrew
- [ ] Install Ollama via Homebrew
- [ ] Clone AppletScriptorium repository
- [ ] Install Python dependencies (system or venv)
- [ ] Install Playwright browsers
- [ ] Start Ollama service
- [ ] Pull granite4:tiny-h model
- [ ] Verify Ollama model available
- [ ] Create runs/ directory
- [ ] Configure Mail.app (if using automation)
- [ ] Grant Accessibility permissions (if using Mail rules)
- [ ] Create ~/.pro-alert-env (if using cron)
- [ ] Run test suite (`pytest Summarizer/tests`)
- [ ] Test with sample fixture
- [ ] Test manual CLI run with 2-3 articles
- [ ] Verify digest.html renders correctly
- [ ] Test email sending (if needed)
- [ ] Set up Mail rule or cron (choose one)
- [ ] Verify automated workflow end-to-end

---

## Next Steps

After completing setup:

1. **For Mail Rule Automation**: Follow `Summarizer/MAIL_RULE_SETUP.md`
2. **For CLI Usage**: See `CLAUDE.md` for development commands
3. **For Custom Topics**: Add new Google Alert topics and adjust Mail rules
4. **For Development**: Activate virtual environment and run tests

## Support

For issues not covered here:
1. Check `README.md` for feature documentation
2. Review `CLAUDE.md` for development guidance
3. Inspect `Summarizer/PRO Alert Summarizer PRD.md` for architecture details
4. Check `runs/*/workflow.log` for pipeline errors
