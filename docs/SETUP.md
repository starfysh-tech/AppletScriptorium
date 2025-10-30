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

**LM Studio (Required)**
- Download from https://lmstudio.ai
- Install and launch the application
- Load a chat model (recommended: llama-3.2-3b-instruct or similar)
- Start the local server (CMD+R or Server tab)

**Command-line tools** — Install via Homebrew:
```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required tools
brew install python@3.11 git

# Optional: Install Ollama for LLM fallback
brew install ollama

# Optional: Install url-to-md for Cloudflare fallback
npm install -g url-to-markdown-cli-tool
```

**Optional Dependencies:**
- `url-to-md` — CLI tool for fetching bot-protected sites as Markdown (Cloudflare bypass)
- `Ollama` — Optional fallback LLM backend if LM Studio fails
- Jina Reader API — Final fallback for bot-protected sites (requires API key)
  - Access https://jina.ai/reader using https://www.browserling.com/
  - Click "API KEY & BILLING" button to sign up and get your key
  - Configure: `cp .env.template .env` and add your `JINA_API_KEY`

### LLM Backend Configuration

**LM Studio Setup (Required)**

1. Download and install LM Studio from https://lmstudio.ai
2. Launch LM Studio and download a model:
   - Click the "Discover" tab
   - Search for "llama-3.2-3b-instruct" (recommended for speed)
   - Or choose any chat model (larger models = better quality but slower)
   - Click "Download"
3. Load the model:
   - Go to "AI Chat" tab
   - Select your downloaded model from the dropdown
4. Start the local server:
   - Press CMD+R or click the "Server" tab
   - Click "Start Server"
   - Note the server URL (typically http://localhost:1234)
5. Configure in `.env`:
   ```bash
   LMSTUDIO_BASE_URL=http://localhost:1234
   LMSTUDIO_MODEL=llama-3.2-3b-instruct  # Use exact model name from LM Studio
   LMSTUDIO_TIMEOUT=30.0
   ```

**Ollama Setup (Optional Fallback)**

Only needed if you want fallback when LM Studio fails:

```bash
# Install Ollama
brew install ollama

# Start Ollama service
brew services start ollama

# Pull a model
ollama pull qwen3:latest
```

Configure in `.env`:
```bash
OLLAMA_ENABLED=true
OLLAMA_MODEL=qwen3:latest
```

**Backend Fallback Behavior:**
- Pipeline tries LM Studio first (if `LMSTUDIO_BASE_URL` configured)
- If LM Studio fails AND `OLLAMA_ENABLED=true`, tries Ollama
- If both fail (or neither configured), pipeline exits with error

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

macOS requires permissions for AppleScript to interact with Mail.app:

#### Manual CLI Usage
**Required:** Automation permission

1. Go to **System Settings** → **Privacy & Security** → **Automation**
2. Enable **Terminal → Mail**

**When to grant:** When first running `python3 -m Summarizer.cli run`

**What it enables:** AppleScript can capture inbox messages

**Note:** Mail rule automation doesn't require any special permissions—it uses SMTP for email delivery instead of UI automation.

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

   **If ALL of the following conditions are met:**
   - **Subject** → **contains** → `Google Alert -`
   - **From** → **is equal to** → `googlealerts-noreply@google.com`

   **Perform the following actions:**
   - Action: **Run AppleScript** → Select `process-alert.scpt`

4. Click **OK**

**Important Notes:**
- **Dual filtering:** Both Subject AND From conditions must match (use "all" not "any" in the rule)
- **Topic filtering:** Mail rule conditions do ALL filtering. Using `Google Alert -` matches ANY Google Alert topic. For topic-specific processing, narrow the subject (e.g., `Google Alert - Medication reminder`)
- **False positives:** Risk is minimal with both conditions—only legitimate Google Alerts will trigger the rule

#### 3. Configure SMTP Email Settings

Set up your email credentials in the `.env` file:

1. Copy the template:
   ```bash
   cp .env.template .env
   ```

2. Edit `.env` and add your SMTP credentials:
   ```bash
   # Gmail example (requires app password)
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-app-password-here
   SMTP_FROM_EMAIL=your-email@gmail.com
   ```

3. **For Gmail**: Generate an app password (regular password won't work):
   - Visit https://myaccount.google.com/apppasswords
   - Create an app password for "Mail"
   - Use this password in `.env` (not your regular Gmail password)

4. Edit the AppleScript to set your digest recipient:
   - Open `~/Library/Application Scripts/com.apple.mail/process-alert.scpt`
   - Find line: `set digestRecipient to "{{EMAIL}}"`
   - Change to your actual email address
   - Save the file

**Security Note:** Never commit `.env` to version control—it contains sensitive credentials.

#### 4. Verify SMTP Configuration

Test your SMTP credentials before using the Mail rule:

```bash
# Run pipeline manually with SMTP sending
python3 -m Summarizer.cli run \
  --output-dir runs/test-$(date +%Y%m%d-%H%M%S) \
  --max-articles 1 \
  --email-digest your-email@example.com \
  --smtp-send
```

If SMTP authentication fails, check:
- `.env` file has correct SMTP credentials
- Gmail users: Using app password (not regular password)
- Firewall/network allows SMTP connections

#### 5. Modifying the Script (Future Changes)

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

#### 6. Test the Rule

**Option A - Manual Test:**
1. Find an existing Google Alert email in inbox
2. Select it
3. **Message** menu → **Apply Rules**

**Option B - Live Test:**
Wait for next Google Alert to arrive - rule triggers automatically

**Expected Behavior:**
Alert arrives → Mail rule triggers → Pipeline runs → Digest sent via SMTP → Trigger email marked as read

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

### Environment Variables Reference

Configuration can come from three sources (highest to lowest priority):

1. **CLI flags** — `--model`, `--email-digest`, `--topic`, etc.
2. **Environment variables** — `ALERT_*` prefix or direct export
3. **.env file** — Persistent defaults (recommended for credentials)

#### Required Variables (.env file)

**LLM Backend (LM Studio):**
```bash
LMSTUDIO_BASE_URL=http://localhost:1234  # LM Studio server URL
LMSTUDIO_MODEL=llama-3.2-3b-instruct     # Model name from LM Studio
LMSTUDIO_TIMEOUT=30.0                     # Request timeout (seconds)
```

**SMTP Email Delivery:**
```bash
SMTP_USERNAME=your-email@gmail.com        # SMTP account username
SMTP_PASSWORD=your-app-password           # Use app password for Gmail
SMTP_HOST=smtp.gmail.com                  # SMTP server hostname
SMTP_PORT=587                             # SMTP port (587 for TLS)
SMTP_FROM_EMAIL=your-email@gmail.com      # Sender email address
```

#### Optional Variables

**Ollama Fallback:**
```bash
OLLAMA_ENABLED=false                      # Set to true to enable Ollama fallback
OLLAMA_MODEL=qwen3:latest                 # Model to use if LM Studio fails
OLLAMA_TIMEOUT=120.0                      # Ollama request timeout (seconds)
```

**Article Fetching:**
```bash
JINA_API_KEY=your-jina-api-key           # Jina Reader API for bot-protected sites
ALERT_HTTP_HEADERS_JSON='{"example.com": {"Cookie": "session=abc"}}'  # Custom headers
```

**Email Configuration:**
```bash
ALERT_DIGEST_EMAIL=recipient@example.com  # Default digest recipient
ALERT_EMAIL_SENDER=sender@example.com     # Default sender address
```

**Example Override:**
```bash
# .env file has LMSTUDIO_MODEL=llama-3.2
# CLI flag --model qwen3:latest overrides it for that run only
# Mail rule automation always uses .env values
```

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
