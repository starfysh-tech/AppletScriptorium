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

### SMTP Authentication Fails

**Issue**: "SMTP authentication failed" or "Connection refused"

**Solutions**:
1. **Check `.env` configuration**:
   ```bash
   cat .env | grep SMTP
   ```
   Verify all SMTP credentials are set correctly

2. **Gmail users**: Must use app password, not regular password:
   - Visit https://myaccount.google.com/apppasswords
   - Create an app password for "Mail"
   - Copy the generated password to `SMTP_PASSWORD` in `.env`

3. **Test SMTP connection manually**:
   ```bash
   python3 -m Summarizer.cli run \
     --output-dir runs/test \
     --max-articles 1 \
     --email-digest your-email@example.com \
     --smtp-send
   ```
   Check `workflow.log` for detailed SMTP error messages

4. **Check firewall**: Ensure port 587 (or your configured port) is not blocked

5. **Non-Gmail providers**: Update `SMTP_HOST` and `SMTP_PORT` in `.env`:
   - Outlook: `smtp-mail.outlook.com:587`
   - Yahoo: `smtp.mail.yahoo.com:587`
   - Custom SMTP: Check your provider's documentation

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

### Digest Email Not Received

**Issue**: Pipeline completes but digest email doesn't arrive

**Solutions**:
1. **Check spam folder**: SMTP-sent emails may be filtered as spam initially
2. **Verify SMTP credentials**: See [SMTP Authentication Fails](#smtp-authentication-fails) above
3. **Check workflow log**:
   ```bash
   cat ~/Code/AppletScriptorium/runs/alert-*/workflow.log
   ```
   Look for "Email sent successfully" or SMTP error messages
4. **Verify email address**: Check recipient address in `process-alert.scpt` line 12
5. **Test locally**: View `digest.html` in run directory to verify content generated correctly

---

## Mail Rule Issues

### Rule Not Triggering

**Issue**: Mail rule doesn't execute automatically

**Solutions**:
1. **Verify Mail rule condition** (most common issue):
   - Open Mail.app → Settings → Rules
   - Ensure rule has: **Subject** → **contains** → `Google Alert -`
   - **Important:** Do NOT add a From condition - this prevents test emails and forwarded alerts from triggering
   - If rule has a From condition, remove it and keep only the Subject condition

2. **Test with actual Google Alert** (not test emails from personal accounts):
   - Test emails from non-Google accounts won't match if you have a From filter
   - Either remove From condition or wait for real Google Alert to arrive

3. Check AppleScript exists:
   ```bash
   ls -la ~/Library/Application\ Scripts/com.apple.mail/process-alert.scpt
   ```

4. Verify script is readable:
   ```bash
   chmod +r ~/Library/Application\ Scripts/com.apple.mail/process-alert.scpt
   ```

5. Test rule manually:
   - Select a message with "Google Alert -" in subject
   - **Message** menu → **Apply Rules**
   - Check for new directory: `ls -lt ~/Code/AppletScriptorium/runs | head -3`
   - If directory created, rule triggered successfully

6. Check Console.app for error messages:
   - Open Console.app → Search for "Mail" → Look for script errors

**Common Mistake:**
Adding a `From equals googlealerts-noreply@google.com` condition prevents testing with emails from other accounts. The subject filter alone is sufficient and safer.

### Mail Rule Notification Shows Error

**Issue**: Notification says "Pipeline failed: [error message]"

**Solutions**:
1. **Check workflow log**:
   ```bash
   cat ~/Code/AppletScriptorium/runs/alert-*/workflow.log
   ```
   Look for the specific error that caused the failure

2. **Common errors**:
   - "SMTP authentication failed" → See [SMTP Authentication Fails](#smtp-authentication-fails)
   - "Ollama unresponsive" → See [Ollama Unresponsive](#ollama-unresponsive-timeout)
   - "Failed to fetch article" → See [Article Fetching Fails](#article-fetching-fails)

3. **Test manually** to isolate the issue:
   ```bash
   python3 -m Summarizer.cli run \
     --output-dir runs/debug \
     --max-articles 1 \
     --smtp-send
   ```

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
