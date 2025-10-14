# Migration Guide — Breaking Changes in v2.0.0

This guide helps existing users migrate from PRO-specific naming to the generic Google Alert Intelligence framework.

## Summary of Changes

**What changed:**
- Renamed environment variables: `PRO_ALERT_*` → `ALERT_*`
- Renamed scripts: `run_pro_alert.sh` → `run_alert.sh`, `process-pro-alert.scpt` → `process-alert.scpt`
- Renamed config file: `~/.pro-alert-env` → `~/.alert-env`
- Updated all documentation to use new names

**Why these changes:**
- Original "PRO Alert Summarizer" naming was specific to Patient Reported Outcomes use case
- Framework now supports ANY Google Alert topic (AI research, climate policy, medication reminders, etc.)
- New "Google Alert Intelligence" branding better reflects the generic capabilities

**Backward compatibility:**
- Old `PRO_ALERT_*` environment variable names still work (fallback support)
- No data loss or workflow disruption
- Migration can be done gradually

---

## Migration Checklist

### For All Users

- [ ] **Read this guide completely** before making changes
- [ ] **Back up your configuration** (copy `~/.pro-alert-env`, AppleScript files)
- [ ] **Test changes in development** before modifying production setup

### For Cron Users

- [ ] Rename `~/.pro-alert-env` to `~/.alert-env`
- [ ] Update variable names in `~/.alert-env` (see [Environment Variables](#environment-variables))
- [ ] Update crontab to reference new script path (see [Cron Jobs](#cron-jobs))
- [ ] Test cron job manually before waiting for scheduled run

### For Mail Rule Users

- [ ] Replace AppleScript file (see [AppleScript Files](#applescript-files))
- [ ] Update Mail rule to reference new script name
- [ ] Grant permissions if prompted
- [ ] Test with sample Google Alert email

---

## Detailed Migration Steps

### Environment Variables

**Old names (deprecated but still functional):**
```bash
PRO_ALERT_OUTPUT_DIR
PRO_ALERT_MODEL
PRO_ALERT_MAX_ARTICLES
PRO_ALERT_DIGEST_EMAIL
PRO_ALERT_EMAIL_SENDER
PRO_ALERT_EMAIL_RECIPIENT
PRO_ALERT_NOTIFY_ON_SUCCESS
PRO_ALERT_HTTP_HEADERS_JSON
```

**New names (recommended):**
```bash
ALERT_OUTPUT_DIR
ALERT_MODEL
ALERT_MAX_ARTICLES
ALERT_DIGEST_EMAIL
ALERT_EMAIL_SENDER
ALERT_EMAIL_RECIPIENT
ALERT_NOTIFY_ON_SUCCESS
ALERT_HTTP_HEADERS_JSON
```

**Migration steps:**
1. Copy your existing config:
   ```bash
   cp ~/.pro-alert-env ~/.alert-env
   ```

2. Edit `~/.alert-env` and replace all variable names:
   ```bash
   sed -i '' 's/PRO_ALERT_/ALERT_/g' ~/.alert-env
   ```

3. Verify the changes:
   ```bash
   cat ~/.alert-env
   ```

4. (Optional) Keep `~/.pro-alert-env` as backup for rollback

**Testing:**
```bash
source ~/.alert-env
echo $ALERT_MODEL  # Should show your configured model
```

### Script Files

**Old paths:**
- `Summarizer/bin/run_pro_alert.sh` → **Now:** `Summarizer/bin/run_alert.sh`
- `process-pro-alert.scpt` → **Now:** `process-alert.scpt`

**What happened:**
- Files were renamed via `git mv` (history preserved)
- Old filenames no longer exist in repository

**No action needed for:**
- Git will handle the rename automatically when you pull/merge

### Cron Jobs

**Old crontab entry:**
```cron
0 7 * * 1-5 /bin/bash -lc 'source ~/.pro-alert-env; /Users/you/Code/AppletScriptorium/Summarizer/bin/run_pro_alert.sh'
```

**New crontab entry:**
```cron
0 7 * * 1-5 /bin/bash -lc 'source ~/.alert-env; /Users/you/Code/AppletScriptorium/Summarizer/bin/run_alert.sh'
```

**Migration steps:**
1. Edit crontab:
   ```bash
   crontab -e
   ```

2. Update the line to reference:
   - `~/.alert-env` instead of `~/.pro-alert-env`
   - `run_alert.sh` instead of `run_pro_alert.sh`

3. Save and verify:
   ```bash
   crontab -l
   ```

4. Test manually:
   ```bash
   source ~/.alert-env
   /Users/you/Code/AppletScriptorium/Summarizer/bin/run_alert.sh
   ```

### AppleScript Files

**Old AppleScript:**
- Location: `~/Library/Application Scripts/com.apple.mail/process-pro-alert.scpt`
- Name: `process-pro-alert.scpt`

**New AppleScript:**
- Location: `~/Library/Application Scripts/com.apple.mail/process-alert.scpt`
- Name: `process-alert.scpt`
- Updated notifications: "Google Alert Intelligence" instead of "PRO Alert Summarizer"

**Migration steps:**

#### Option A: Use setup-mail-rule.sh (Recommended)
```bash
cd ~/Code/AppletScriptorium
./setup-mail-rule.sh
```
This recreates the AppleScript with the new name and prompts for your email.

#### Option B: Manual update
1. Remove old script:
   ```bash
   rm ~/Library/Application\ Scripts/com.apple.mail/process-pro-alert.scpt
   ```

2. Copy new template:
   ```bash
   cp Summarizer/templates/process-alert.scpt \
      ~/Library/Application\ Scripts/com.apple.mail/process-alert.scpt
   ```

3. Edit and replace `{{EMAIL}}` placeholder with your actual email address

4. Update Mail rule:
   - Open Mail.app → Mail → Settings → Rules
   - Find your Google Alert rule
   - Update **Action**: Change from `process-pro-alert.scpt` to `process-alert.scpt`
   - Click OK

5. Test the rule:
   - Select an existing Google Alert email
   - Message → Apply Rules
   - Verify digest is generated and sent

---

## Rollback Instructions

If you encounter issues and need to roll back:

### For Cron Users
1. Restore old environment file:
   ```bash
   cp ~/.pro-alert-env.backup ~/.pro-alert-env
   ```

2. Revert crontab changes:
   ```bash
   crontab -e
   # Change back to old paths
   ```

3. Git checkout previous version:
   ```bash
   git checkout v1.0.0  # Or your last working commit
   ```

### For Mail Rule Users
1. Copy old AppleScript back:
   ```bash
   cp ~/path/to/backup/process-pro-alert.scpt \
      ~/Library/Application\ Scripts/com.apple.mail/
   ```

2. Update Mail rule to use old script name

3. Git checkout previous version

---

## Verification

After migration, verify everything works:

### 1. Check Environment Variables
```bash
source ~/.alert-env
env | grep ALERT_
# Should show your ALERT_* variables
```

### 2. Run Manual Test
```bash
python3 -m Summarizer.cli run \
  --output-dir runs/migration-test \
  --max-articles 2 \
  --subject-filter "Google Alert -"
```

### 3. Verify Output
```bash
ls -la runs/migration-test/
# Should contain: alert.eml, articles/, digest.html, workflow.log
```

### 4. Test Email Delivery (if configured)
```bash
python3 -m Summarizer.cli run \
  --output-dir runs/email-test \
  --max-articles 1 \
  --email-digest your-email@example.com \
  --email-sender your-email@example.com \
  --subject-filter "Google Alert -"
# Check Mail.app Sent folder
```

### 5. Run Test Suite
```bash
python3 -m pytest Summarizer/tests
# All tests should pass
```

---

## Troubleshooting

### "Command not found: run_alert.sh"
- **Cause:** Old cron entry or script path
- **Fix:** Update crontab to use `Summarizer/bin/run_alert.sh`

### "No such file: process-alert.scpt"
- **Cause:** Mail rule references old script name
- **Fix:** Update Mail rule action to use `process-alert.scpt`

### Environment variables not working
- **Cause:** Sourcing wrong file or using old variable names
- **Fix:**
  1. Verify `~/.alert-env` exists: `ls -la ~/.alert-env`
  2. Check variable names use `ALERT_*` prefix
  3. Re-source: `source ~/.alert-env`

### Mail rule not triggering
- **Cause:** AppleScript permissions or file location
- **Fix:**
  1. Verify script exists: `ls -la ~/Library/Application\ Scripts/com.apple.mail/process-alert.scpt`
  2. Check Mail rule action references correct script
  3. Verify Accessibility permissions (System Settings → Privacy & Security → Accessibility)

### Tests failing
- **Cause:** Code/fixture mismatch
- **Fix:**
  ```bash
  git pull origin main  # Get latest changes
  python3 -m pip install -r Summarizer/requirements.txt
  python3 -m pytest Summarizer/tests -v  # Run with verbose output
  ```

---

## Support

For issues not covered here:
1. Check [SETUP.md](./SETUP.md) for configuration details
2. Review [Summarizer/MAIL_RULE_SETUP.md](./Summarizer/MAIL_RULE_SETUP.md) for Mail automation
3. Inspect `runs/*/workflow.log` for pipeline errors
4. Verify backward compatibility layer is working (old env vars should still work)

## What Stays the Same

The following did NOT change:
- Python code behavior (same article fetching, summarization, digest rendering)
- Ollama model (`granite4:tiny-h`)
- Output directory structure (`runs/<timestamp>/`)
- CLI flags (`--output-dir`, `--model`, `--max-articles`, etc.)
- Test fixtures and test suite
- Mail rule conditions (From/Subject patterns)
- AppleScript integration approach
- Parallel processing (5 workers)
- Playwright/Crawlee fallback behavior
