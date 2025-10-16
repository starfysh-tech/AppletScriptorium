# Troubleshooting Guide

Common issues and solutions for AppletScriptorium Google Alert Intelligence.

## Table of Contents
- [Installation Issues](#installation-issues)
- [Permission Issues](#permission-issues)
- [Pipeline Issues](#pipeline-issues)
- [Mail Rule Issues](#mail-rule-issues)
- [Article Fetching Issues](#article-fetching-issues)

---

## Installation Issues

### Manual Installation

If automated setup (`./install.sh`) fails, see **[SETUP.md](./SETUP.md#manual-installation)** for step-by-step manual installation instructions.

### Ollama Model Not Found

**Issue**: `ollama list` doesn't show qwen3:latest

**Solutions**:
```bash
# Start Ollama service
brew services start ollama

# Wait 5 seconds, then pull model
ollama pull qwen3:latest

# If pull hangs, check network connection and retry
```

### url-to-md CLI Not Found

**Issue**: `url-to-md: command not found`

**Solutions**:
```bash
# Install via npm (recommended)
npm install -g url-to-markdown-cli-tool

# Confirm installation works
url-to-md https://example.com --wait 2 | head
```

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

### Verification Steps

If you need to manually verify the installation:

**1. Verify Python Installation**
```bash
which python3
# Should show: /usr/local/bin/python3 or /opt/homebrew/bin/python3

python3 --version
# Should show: Python 3.11.x or higher
```

**2. Verify Python Packages**
```bash
python3 -m pip list | grep -E "beautifulsoup4|httpx|readability"
```

Expected output:
```
beautifulsoup4       4.13.4
httpx                0.27.x
readability-lxml     0.8.x
markdownify          0.12.x
```

**3. Verify Ollama**
```bash
# Check if Ollama service is running
brew services list | grep ollama
# Should show: ollama started

# List installed models
ollama list
# Should show: qwen3:latest

# Test model
echo "Summarize: AI assistants are transforming software development" | ollama run qwen3:latest
```

**4. Verify url-to-md CLI**
```bash
url-to-md https://example.com --wait 2 | head
# Should print article text converted to Markdown
```

---

## Permission Issues

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

### Mail Rule Accessibility Permission

**Issue**: Mail rule runs but email doesn't send

**Solution**:
1. Go to **System Settings** → **Privacy & Security** → **Accessibility**
2. Look for **Mail** in the list
3. If not present, click **+** and add `/Applications/Mail.app`
4. Ensure the checkbox is enabled

Without this permission, the automated copy-paste will fail.

---

## Pipeline Issues

### Pipeline Fails

Check the log file:
```bash
ls -lt ~/Code/AppletScriptorium/runs/
cat ~/Code/AppletScriptorium/runs/alert-*/workflow.log
```

Common issues:
- Python dependencies not installed (check `pip3 list`)
- Ollama not running (`brew services start ollama`)
- Model not installed (`ollama pull qwen3:latest`)

### Ollama Unresponsive (Timeout)

**Issue**: Pipeline hangs or times out with `"Ollama unresponsive (timeout after 120s)"`

This occurs when Ollama daemon becomes unresponsive—typically after extended uptime or stuck processes.

**Automatic Recovery**:
The pipeline now detects Ollama hangs and auto-recovers:
1. **Detection**: Timeout after 120 seconds waiting for Ollama
2. **Logged**: `"Ollama unresponsive (timeout after 120s); attempting restart"`
3. **Auto-restart**: Kills unresponsive process; launchd relaunches it automatically
4. **Retry**: Retries summarization once after restart
5. **Clear error**: If recovery fails, error message indicates the issue

**Manual Fix** (if auto-recovery doesn't work):
```bash
# Kill the unresponsive process (launchd will auto-restart it)
pkill -f "ollama serve"

# Wait for restart and verify
sleep 3
ps aux | grep "ollama serve" | grep -v grep

# Or restart via Homebrew
brew services restart ollama

# Verify it responds
echo "test" | ollama run qwen3:latest
```

**Prevention**:
- Restart Ollama periodically: `brew services restart ollama`
- Monitor uptime: `ps aux | grep ollama` (check ETIME column)
- Set up cron job for daily restarts:
  ```bash
  # Add to crontab (crontab -e)
  0 2 * * * brew services restart ollama
  ```

### Digest Not Rendering

If the .eml viewer doesn't open automatically:
1. Check the run output directory: `~/Code/AppletScriptorium/runs/alert-TIMESTAMP/`
2. Verify both `digest.html` and `digest.eml` files exist
3. Manually open `digest.eml` to verify HTML renders correctly

---

## Mail Rule Issues

### Rule Not Triggering

**Issue**: Mail rule doesn't execute automatically

**Solutions**:
1. Verify Mail rule conditions match incoming emails exactly:
   - **From**: `googlealerts-noreply@google.com`
   - **Subject**: `Google Alert -`
2. Check AppleScript exists:
   ```bash
   ls -la ~/Library/Application\ Scripts/com.apple.mail/process-alert.scpt
   ```
3. Verify script is readable:
   ```bash
   chmod +r ~/Library/Application\ Scripts/com.apple.mail/process-alert.scpt
   ```
4. Test rule manually:
   - Select a Google Alert email in Mail.app
   - **Message** menu → **Apply Rules**
5. Check Console.app for error messages:
   - Open Console.app → Search for "Mail" → Look for script errors

### Digest Email Not Sending

**Issue**: digest.eml created but email not sent

**Solutions**:
1. **Check Accessibility permissions**: System Settings → Privacy & Security → Accessibility → enable Mail.app
2. **Check notification**: Look for error message (should say "Google Alert digest sent" or "Message created but not sent")
3. **Check Sent folder**: Verify email actually sent and has correct formatting
4. **Check compose window**: If notification says "not sent", check if compose window is still open with content
5. **Test manually**:
   - Open `digest.eml`
   - Copy content (Cmd+A, Cmd+C)
   - Paste into new email to verify formatting

Common causes:
- Accessibility permissions not granted (body field focus fails)
- Insufficient delays (script tries to send before paste completes)
- Mail.app account not configured for sending
- Compose window didn't receive focus (increase delay after creating window)

**Debug steps:**
1. Check workflow log: `~/Code/AppletScriptorium/runs/alert-TIMESTAMP/workflow.log`
2. Verify .eml file exists and opens correctly when double-clicked
3. Test clipboard: After opening .eml, manually do Cmd+A, Cmd+C - should copy ~6000+ characters
4. Check if bold labels appear when viewing .eml file (if not, HTML rendering issue)

### Increasing Delays in AppleScript

If the email sends but is blank or has formatting issues, increase delays:

1. Open Script Editor
2. File → Open → Navigate to `~/Library/Application Scripts/com.apple.mail/process-alert.scpt`
3. Find delay commands and increase values:
   ```applescript
   delay 2  -- Increase to 3 or 4
   ```
4. Save and test again

---

## Article Fetching Issues

### Article Fetching Fails

**Issue**: "Failed to fetch {url}"

**Solutions**:
1. Check network connection
2. For sites requiring authentication, set custom headers:
   ```bash
   export ALERT_HTTP_HEADERS_JSON='{"example.com": {"Cookie": "session=abc"}}'
   ```
3. Verify `url-to-md` CLI works for the URL:
   ```bash
   url-to-md "https://example.com" --wait 5 | head
   ```
4. Ensure `JINA_API_KEY` is set for Jina fallback (export in shell or launchd plist)
5. Increase timeout in config if needed

### Custom HTTP Headers

For sites requiring cookies or authentication:

```bash
# Add to ~/.zshrc or ~/.bash_profile
export ALERT_HTTP_HEADERS_JSON='{"example.com": {"Cookie": "session=abc", "Authorization": "Bearer token"}}'

# Or for Mail rule automation, edit process-alert.scpt:
set pythonCmd to "export ALERT_HTTP_HEADERS_JSON='{...}' && cd " & quoted form of repoPath & "..."
```

---

## Getting More Help

If issues persist:
1. Check `runs/*/workflow.log` for detailed error messages
2. Run with verbose output: `python3 -m Summarizer.cli run --output-dir runs/test --max-articles 1`
3. Review Console.app logs when Mail rule runs
4. Verify all prerequisites in SETUP.md
5. Check configuration in `Summarizer/config.py`
