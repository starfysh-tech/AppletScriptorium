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

3. **UV** (fast Python package manager)
   ```bash
   brew install uv
   ```

4. **Ollama** (local LLM runtime)
   ```bash
   brew install ollama
   ```

5. **Git** (likely already installed)
   ```bash
   git --version  # Verify installation
   ```

### Optional Tools
- **jq** (for JSON inspection): `brew install jq`
- **pytest** (for running tests): Included in requirements.txt

---

## Installation Steps

### Automated Setup (Recommended)

The easiest way to set up Google Alert Intelligence is using the automated installation scripts:

```bash
# 1. Clone repository
cd ~/Code  # Or your preferred project directory
git clone https://github.com/yourusername/AppletScriptorium.git
cd AppletScriptorium

# 2. Run automated installer
./install.sh

# 3. Set up Mail rule automation (interactive)
./setup-mail-rule.sh

# 4. Validate installation
./validate.sh
```

The `install.sh` script automates:
- Checking prerequisites (Homebrew, Python 3.11+, Ollama, Git)
- Installing Python dependencies
- Installing Playwright browsers
- Starting Ollama and pulling granite4:tiny-h model
- Making scripts executable
- Running test suite

For detailed manual installation steps, see the [Manual Installation](#manual-installation) section below.

---

### Manual Installation

If you prefer manual setup or need to troubleshoot:

#### 1. Clone Repository
```bash
cd ~/Code
git clone https://github.com/yourusername/AppletScriptorium.git
cd AppletScriptorium
```

#### 2. Install Python Dependencies
```bash
# System Python (for Mail rule automation) with UV
UV_SYSTEM_PYTHON=true uv pip install --python python3 -r Summarizer/requirements.txt
```

**Required packages:** beautifulsoup4, pytest, httpx, readability-lxml, markdownify, crawlee, browserforge, apify_fingerprint_datapoints

**Note:** UV is ~10-100x faster than pip. `UV_SYSTEM_PYTHON=true` tells UV to use system Python with user site-packages (like `pip install --user`), required for Mail rule automation.

#### 3. Install Playwright
```bash
python3 -m playwright install
```

Downloads Chromium browsers for headless fetching (~200MB).

#### 4. Install Ollama Model
```bash
brew services start ollama
ollama pull granite4:tiny-h
ollama list | grep granite4  # Verify
```

#### 5. Make Scripts Executable
```bash
chmod +x install.sh setup-mail-rule.sh validate.sh
chmod +x Summarizer/fetch-alert-source.applescript
chmod +x run_workflow.sh Summarizer/bin/run_alert.sh
```

#### 6. Create Directories
```bash
mkdir -p runs
```

---

## Configuration

### Mail.app Setup (for automation)

#### For Mail Rule Automation (Recommended)

The `setup-mail-rule.sh` script automates Mail rule configuration:

```bash
./setup-mail-rule.sh
```

This creates `~/Library/Application Scripts/com.apple.mail/process-alert.scpt` and provides step-by-step instructions.

**Manual steps after running setup-mail-rule.sh:**
1. Open Mail.app → Mail → Settings → Rules → Add Rule
2. Configure:
   - **From**: `googlealerts-noreply@google.com`
   - **Subject**: `Google Alert -`
   - **Action**: Run AppleScript → `process-alert.scpt`
3. Grant Accessibility permissions:
   - System Settings → Privacy & Security → Accessibility
   - Add Mail.app and enable

See detailed instructions in: `Summarizer/MAIL_RULE_SETUP.md`

#### For Cron Automation (Alternative)

1. Copy template and customize:
   ```bash
   cp Summarizer/templates/alert-env.template ~/.alert-env
   # Edit ~/.alert-env with your email address and preferences
   ```

2. Edit crontab:
   ```bash
   crontab -e
   ```

3. Add cron entry (weekdays at 7 AM):
   ```cron
   0 7 * * 1-5 /bin/bash -lc 'source ~/.alert-env; /Users/YOUR_USERNAME/Code/AppletScriptorium/Summarizer/bin/run_alert.sh'
   ```

   **Replace `YOUR_USERNAME`** with your actual macOS username.

### Environment Variables (Optional)

Add to `~/.zshrc` or `~/.bash_profile` for CLI usage:

```bash
# Google Alert Intelligence Configuration
export ALERT_MODEL="granite4:tiny-h"
export ALERT_DIGEST_EMAIL="your-email@example.com"
export ALERT_EMAIL_SENDER="your-email@example.com"

# Custom HTTP headers (for sites requiring authentication)
export ALERT_HTTP_HEADERS_JSON='{"example.com": {"Cookie": "session=abc"}}'
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

# Test model (optional - works with any content)
echo "Summarize: AI assistants are transforming software development workflows" | ollama run granite4:tiny-h
```

### 4. Verify Playwright
```bash
python3 -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"
# Should print: Playwright OK
```

### 5. Run Tests
```bash
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

**Issue**: `uv pip install` fails with compilation or permission errors

**Solutions**:
```bash
# Ensure UV is installed
brew install uv

# Install Xcode Command Line Tools (if missing)
xcode-select --install

# Retry installation (UV_SYSTEM_PYTHON=true uses system Python with user site-packages)
UV_SYSTEM_PYTHON=true uv pip install --python python3 -r Summarizer/requirements.txt
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
   export ALERT_HTTP_HEADERS_JSON='{"example.com": {"Cookie": "session=abc"}}'
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
   ls -la ~/Library/Application\ Scripts/com.apple.mail/process-alert.scpt
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
2. Increase delays in process-alert.scpt
3. Test manually:
   ```bash
   open runs/*/digest.eml
   # Verify HTML renders in Mail.app viewer
   ```

---

## Next Steps

After completing setup:

1. **For Mail Rule Automation**: Follow `Summarizer/MAIL_RULE_SETUP.md`
2. **For CLI Usage**: See `CLAUDE.md` for development commands
3. **For Multiple Topics**: Subscribe to Google Alerts on any topics you want—Mail rules automatically process all alerts
4. **For Development**: Activate virtual environment and run tests

## Support

For issues not covered here:
1. Check `README.md` for feature documentation
2. Review `CLAUDE.md` for development guidance
3. Inspect `Summarizer/PRO Alert Summarizer PRD.md` for architecture details (note: documents original Patient Reported Outcomes use case, but framework now supports any Google Alert topic)
4. Check `runs/*/workflow.log` for pipeline errors
