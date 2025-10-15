# AppletScriptorium Setup Guide

Complete instructions for setting up AppletScriptorium on macOS.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Verification](#verification)
- [First Run](#first-run)

---

## Prerequisites

### System Requirements
- macOS 12.0 (Monterey) or later
- Python 3.11 or later
- Mail.app configured with at least one email account
- ~2GB disk space for dependencies and models

### Required Tools

Install via Homebrew:
```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required tools
brew install python@3.11 ollama git

# Optional: Install url-to-md for Cloudflare fallback
npm install -g url-to-markdown-cli-tool
```

**Optional Dependencies:**
- `url-to-md` — CLI tool for fetching bot-protected sites as Markdown (Cloudflare bypass)
- Jina Reader API — Final fallback for bot-protected sites (requires API key)
  - Access https://jina.ai/reader using https://www.browserling.com/
  - Click "API KEY & BILLING" button to sign up and get your key
  - Configure: `cp .env.template .env` and add your `JINA_API_KEY`

---

## Installation

### Automated Setup (Recommended)

```bash
# 1. Clone repository
cd ~/Code
git clone https://github.com/yourusername/AppletScriptorium.git
cd AppletScriptorium

# 2. Run automated installer
./install.sh

# 3. Set up Mail rule automation
./setup-mail-rule.sh

# 4. Validate installation
./validate.sh
```

The `install.sh` script automates:
- Checking prerequisites
- Installing Python dependencies
- Starting Ollama and pulling qwen3:latest model
- Making scripts executable
- Running test suite

### Manual Installation

If automated setup fails or you need manual control:

```bash
# 1. Clone repository
cd ~/Code
git clone https://github.com/yourusername/AppletScriptorium.git
cd AppletScriptorium

# 2. Install Python dependencies (system Python with --user flag)
python3 -m pip install --user -r Summarizer/requirements.txt

# 3. Install and start Ollama
brew services start ollama
ollama pull qwen3:latest

# 4. Optional: Install url-to-md for Cloudflare fallback
npm install -g url-to-markdown-cli-tool

# 5. Make scripts executable
chmod +x install.sh setup-mail-rule.sh validate.sh run_workflow.sh
chmod +x Summarizer/fetch-alert-source.applescript Summarizer/bin/run_alert.sh

# 6. Create output directory
mkdir -p runs

# 7. Optional: Configure environment variables
cp .env.template .env
# Edit .env to add your JINA_API_KEY (for Cloudflare fallback)

# 8. Run tests
python3 -m pytest Summarizer/tests
```

**Note:** The `--user` flag installs packages to user site-packages, which is required for Mail rule automation (venv not supported).

---

## Configuration

### System Permissions

macOS requires different permissions depending on how you run the pipeline:

#### Mail Rule Automation (Recommended)
**Required:** Accessibility permission

1. Go to **System Settings** → **Privacy & Security** → **Accessibility**
2. Look for **Mail** in the list
3. If not present, click **+** and add `/Applications/Mail.app`
4. Ensure the checkbox is enabled

**When to grant:** After running `./setup-mail-rule.sh` and creating the Mail rule

**What it enables:** AppleScript automation of keyboard actions (copy/paste digest into compose window)

#### Manual CLI Usage
**Required:** Automation permission

1. Go to **System Settings** → **Privacy & Security** → **Automation**
2. Enable **Terminal → Mail**

**When to grant:** When first running `python3 -m Summarizer.cli run`

**What it enables:** AppleScript can capture inbox messages

**Note:** If using both modes, you'll need both permissions.

---

### Mail Rule Automation (Recommended)

Event-driven processing that triggers automatically when Google Alerts arrive.

#### 1. Verify AppleScript Installation

The `setup-mail-rule.sh` script should have installed the AppleScript:

```bash
ls -la ~/Library/Application\ Scripts/com.apple.mail/process-alert.scpt
```

If missing, run `./setup-mail-rule.sh` again.

#### 2. Create Mail Rule

1. Open **Mail.app** → **Settings** → **Rules** tab
2. Click **Add Rule**
3. Configure:

   **Description:** `Process Google Alert`

   **If all of the following conditions are met:**
   - Condition 1: **From** → **Contains** → `googlealerts-noreply@google.com`
   - Condition 2: **Subject** → **Contains** → `Google Alert -`

   **Perform the following actions:**
   - Action: **Run AppleScript** → Select `process-alert.scpt`

4. Click **OK**

**Note:** Mail rule conditions do ALL filtering. Using `Google Alert -` matches ANY Google Alert topic. For topic-specific processing, narrow the subject (e.g., `Google Alert - Medication reminder`).

#### 3. Configure Email Recipient

Edit the AppleScript to set your email address:

1. Open **Script Editor**
2. **File** → **Open** → Navigate to `~/Library/Application Scripts/com.apple.mail/process-alert.scpt`
3. Find line: `set digestRecipient to "user@example.com"`
4. Change to your actual email address
5. **File** → **Save**

#### 4. Modifying the Script (Future Changes)

**Understanding the two files:**
- **Template:** `Summarizer/templates/process-alert.scpt` (source of truth in repository)
- **Installed:** `~/Library/Application Scripts/com.apple.mail/process-alert.scpt` (what Mail.app uses)

**When making changes to behavior, subject line, or logic:**

**Option A - Update template and reinstall (Recommended):**
```bash
# 1. Edit the template
open Summarizer/templates/process-alert.scpt

# 2. Make your changes and save

# 3. Re-run setup to install updated script
./setup-mail-rule.sh
```

**Option B - Direct edit (Quick fix):**
```bash
# Edit installed script directly
open ~/Library/Application\ Scripts/com.apple.mail/process-alert.scpt
```

**⚠️ Important:** Changes to installed script are overwritten by `setup-mail-rule.sh`. Always update the template if you want changes to persist across reinstalls.

#### 5. Grant Accessibility Permission

See [System Permissions](#system-permissions) above.

#### 6. Test the Rule

**Option A - Manual Test:**
1. Find an existing Google Alert email in inbox
2. Select it
3. **Message** menu → **Apply Rules**

**Option B - Live Test:**
Wait for next Google Alert to arrive - rule triggers automatically

**Expected Behavior:**
Alert arrives → Mail rule triggers → Pipeline runs → Digest email sent automatically → Trigger email marked as read

---

### Cron Scheduling (Alternative)

For fixed-schedule digests instead of event-driven processing.

**Note:** The `~/.alert-env` file is ONLY needed for cron automation. Not required for Mail rule automation or direct CLI usage.

#### 1. Create Configuration File

```bash
cp Summarizer/templates/alert-env.template ~/.alert-env
# Edit ~/.alert-env with your preferences
```

#### 2. Add Cron Job

```bash
crontab -e
```

Add entry (weekdays at 7 AM):
```cron
0 7 * * 1-5 /bin/bash -lc 'source ~/.alert-env; /Users/YOUR_USERNAME/Code/AppletScriptorium/Summarizer/bin/run_alert.sh'
```

**Replace `YOUR_USERNAME`** with your actual macOS username.

#### 3. Environment Variables

Edit `~/.alert-env`:
```bash
# Required for email notifications
ALERT_EMAIL_RECIPIENT="your-email@example.com"

# Optional settings
ALERT_MODEL="qwen3:latest"
ALERT_MAX_ARTICLES=10
ALERT_DIGEST_EMAIL="recipient1@example.com,recipient2@example.com"
ALERT_EMAIL_SENDER="sender@example.com"
```

**Note:** For Jina Reader API configuration, use `.env` file instead (see Prerequisites section).

---

## Verification

Run the validation script:

```bash
./validate.sh
```

This checks:
- Python 3.11+ installed
- Required packages installed
- Ollama running with qwen3:latest model
- All tests passing

**If validation fails:** See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

---

## First Run

### Test with Sample

```bash
# Parse sample alert (no network calls required)
python3 Summarizer/clean-alert.py \
  Summarizer/Samples/google-alert-sample-2025-10-06.eml | head
```

### Manual CLI Run

Requires Google Alert in Mail.app inbox:

```bash
python3 -m Summarizer.cli run \
  --output-dir runs/test-$(date +%Y%m%d-%H%M%S) \
  --max-articles 3 \
  --subject-filter "Google Alert -"
```

Check outputs:
```bash
ls -la runs/test-*/
# Should contain: alert.eml, alert.tsv, articles/, digest.html, digest.txt, workflow.log
```

View digest:
```bash
open runs/test-*/digest.html
```

---

## Next Steps

1. **Subscribe to Google Alerts** on topics you want to track
2. **Mail rule automation** processes alerts automatically when they arrive
3. **Multiple topics** work out of the box - one rule handles all Google Alert subjects
4. **Customize** configuration in `Summarizer/config.py` if needed
5. **Troubleshooting** → See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

---

## Support

- **Issues during setup**: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- **Development**: [CLAUDE.md](./CLAUDE.md) or [AGENTS.md](./AGENTS.md)
- **Usage examples**: [README.md](./README.md)
- **Pipeline errors**: Check `runs/*/workflow.log`
