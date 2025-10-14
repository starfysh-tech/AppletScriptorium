# Mail Rule Setup for Google Alert Intelligence

This guide explains how to configure Mail.app to automatically process Google Alerts using Mail rules instead of cron scheduling.

**Framework scope:** This Summarizer works with ANY Google Alert topic. Mail rule conditions do the filtering—the code processes whatever alert triggers it.

## Benefits

- **Event-driven**: Processes alerts immediately when they arrive
- **Works with any topic**: One rule handles all Google Alerts, or create separate rules per topic
- **Easy management**: Enable/disable processing per topic via Mail preferences
- **No cron needed**: Mail.app handles all scheduling

## Prerequisites

- Python 3 installed with required dependencies (see `Summarizer/requirements.txt`)
- Ollama running with `granite4:tiny-h` model installed
- AppleScript file exists: `~/Library/Application Scripts/com.apple.mail/process-alert.scpt`

**Note:** The script uses system Python (`/usr/local/bin/python3`). No virtual environment needed.

## Setup Instructions

### 1. Verify AppleScript Installation

The setup script should already be in place at:
```
~/Library/Application Scripts/com.apple.mail/process-alert.scpt
```

If not, the file was created during setup. You can verify with:
```bash
ls -la ~/Library/Application\ Scripts/com.apple.mail/process-alert.scpt
```

### 2. Create Mail Rule

1. Open **Mail.app**
2. Go to **Mail** menu → **Settings** (or **Preferences**)
3. Click the **Rules** tab
4. Click **Add Rule**
5. Configure the rule:

   **Description:**
   ```
   Process Google Alert
   ```

   **If all of the following conditions are met:**
   - Condition 1: **From** → **Contains** → `googlealerts-noreply@google.com`
   - Condition 2: **Subject** → **Contains** → `Google Alert -`

   **Important:** The Mail rule conditions do ALL filtering. The AppleScript has no hardcoded subject patterns—it processes whatever message triggered the rule. Using `Google Alert -` (with trailing space and dash) matches ANY Google Alert topic. For topic-specific processing, narrow the subject (e.g., `Google Alert - Medication reminder`).

   **Perform the following actions:**
   - Action: **Run AppleScript** → Select `process-alert.scpt`

6. Click **OK**

### 3. Configure Recipient

Edit the AppleScript to set your email recipient:

1. Open Script Editor
2. File → Open → Navigate to `~/Library/Application Scripts/com.apple.mail/process-alert.scpt`
3. Find line 21: `set digestRecipient to "user@example.com"`
4. Change to your actual email address
5. File → Save

For multiple recipients, modify the script:
```applescript
set digestRecipients to {"recipient1@example.com", "recipient2@example.com"}

-- In the message creation section:
repeat with recipient in digestRecipients
    tell newMessage
        make new to recipient with properties {address:recipient}
    end tell
end repeat
```

### 4. Grant System Events Permissions

The script needs permission to automate keyboard actions:

1. Go to **System Settings** → **Privacy & Security** → **Accessibility**
2. Look for **Mail** in the list
3. If not present, click **+** and add `/Applications/Mail.app`
4. Ensure the checkbox is enabled

Without this permission, the automated copy-paste will fail.

### 5. Test the Rule

#### Option A: Manual Test
1. Find an existing Google Alert email in your inbox
2. Select it
3. Go to **Message** menu → **Apply Rules**
4. The rule should execute immediately

#### Option B: Live Test
Wait for the next Google Alert to arrive - the rule will trigger automatically.

### Expected Behavior

When a Google Alert arrives (any topic), the process is **fully automated**:
1. Mail rule detects the email
2. AppleScript runs the Python pipeline (generates digest.html and digest.eml)
3. .eml file opens briefly in Mail (to render HTML)
4. Rendered HTML is automatically copied from viewer
5. Viewer closes
6. New compose window is created with placeholder text
7. Body field is focused programmatically
8. Rendered HTML is pasted into body (preserving bold labels and formatting)
9. Email is automatically sent via Cmd+Shift+D keyboard shortcut
10. You receive notification: "Google Alert digest sent to user@example.com"
11. The trigger email is marked as read

**No manual intervention required!** The entire workflow runs automatically from alert arrival to email delivery—regardless of the alert topic.

**Technical Note:** The workflow uses MIME .eml files to render HTML, then copies/pastes into a compose window. This preserves HTML formatting (bold labels, colors) while working around Mail.app's broken `html content` property. The body field is focused programmatically via `set focused of AXWebArea to true`, enabling automated paste.

## Adding Additional Topics

**One rule handles all topics** — The rule configured above (matching `Google Alert -`) will trigger for ANY Google Alert topic:
- Google Alert - Medication reminder
- Google Alert - Artificial intelligence
- Google Alert - Climate change
- Google Alert - Tech industry news
- Any other Google Alert topics you create

The AppleScript automatically processes whatever alert email triggered the rule. No additional configuration needed—just subscribe to new Google Alerts and they'll be processed automatically.

**Optional: Topic-specific customization**
If you need different settings per topic (different recipients, models, output directories), create separate rules and AppleScripts:

```bash
cp ~/Library/Application\ Scripts/com.apple.mail/process-alert.scpt \
   ~/Library/Application\ Scripts/com.apple.mail/process-ai-alerts.scpt
```

Then create a second Mail rule with subject `Google Alert - Artificial intelligence` and action pointing to the new script.

## Troubleshooting

### Rule Not Triggering

1. **Check rule conditions**: Ensure both "From" and "Subject" match your Google Alerts
2. **Verify script location**: Script must be in `~/Library/Application Scripts/com.apple.mail/`
3. **Check permissions**: Ensure script is readable
4. **Test manually**: Select an alert and use Message → Apply Rules

### Pipeline Fails

Check the log file:
```bash
ls -lt ~/Code/AppletScriptorium/runs/
cat ~/Code/AppletScriptorium/runs/alert-*/workflow.log
```

Common issues:
- Python dependencies not installed (check `pip3 list`)
- Ollama not running (`ollama serve`)
- Model not installed (`ollama pull granite4:tiny-h`)

### Digest Not Rendering

If the .eml viewer doesn't open automatically:
1. Check the run output directory: `~/Code/AppletScriptorium/runs/alert-TIMESTAMP/`
2. Verify both `digest.html` and `digest.eml` files exist
3. Manually open `digest.eml` to verify HTML renders correctly

### Email Not Sending

If the digest generates but email doesn't send:

1. **Check System Events permissions**: Go to System Settings → Privacy & Security → Accessibility, ensure Mail.app is enabled
2. **Check notification**: Look for error message in notification (should say "Google Alert Intelligence digest sent" or "Message created but not sent")
3. **Check Sent folder**: Verify email actually sent and has correct formatting
4. **Check compose window**: If notification says "not sent", check if compose window is still open with content
5. **Test manually**: Open `digest.eml`, copy content (Cmd+A, Cmd+C), paste into new email to verify formatting

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

## Disabling Automatic Processing

To temporarily disable:
1. Open Mail.app → Settings → Rules
2. Uncheck the rule to disable
3. Or delete the rule entirely

The digest HTML files remain in `runs/` directory for manual processing.

## Environment Variables

The AppleScript inherits environment from Mail.app, not your shell. To customize:

Edit `process-alert.scpt` and add environment setup:
```applescript
set pythonCmd to "export ALERT_MODEL=qwen3:latest && cd " & quoted form of repoPath & " && /usr/local/bin/python3 -m Summarizer.cli run --output-dir " & quoted form of outputDir
```

Supported variables:
- `ALERT_MODEL`: Ollama model name
- `ALERT_MAX_ARTICLES`: Cap on articles processed
- `ALERT_HTTP_HEADERS_JSON`: Custom HTTP headers for fetching

## Manual CLI Usage

You can still run the pipeline manually without triggering the Mail rule:
```bash
cd ~/Code/AppletScriptorium
python3 -m Summarizer.cli run \
  --output-dir runs/manual-$(date +%Y%m%d-%H%M%S) \
  --email-digest user@example.com \
  --subject-filter "Medication reminder"
```

This creates both `digest.html` and `digest.eml` files in the output directory. Works with any Google Alert topic you specify in `--subject-filter`.

**To send the digest manually:**
1. Double-click `digest.eml` to open in Mail
2. Verify HTML renders correctly (bold labels visible)
3. Copy content: Cmd+A, Cmd+C
4. Create new email in Mail
5. Paste into body: Cmd+V
6. Send

**Note:** The full automation only works when triggered via Mail rule, which runs the AppleScript with proper Mail.app context and Accessibility permissions for UI automation.
