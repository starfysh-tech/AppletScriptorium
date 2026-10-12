#!/bin/bash
# Install a launchd agent that pulls main and runs tiktok_recipes.py every hour, which also publishes the site.
# The pull is how merges to main reach the site. It is fast-forward only, so local edits or another branch
# make it fail without touching the checkout; the run then uses the local code.
# Usage: TikTokRecipes/install_hourly.sh '<collection-url>'
# Remove: launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.starfysh.tiktokrecipes.plist
set -euo pipefail

URL="${1:?usage: install_hourly.sh <collection-url>}"
DIR="$(cd "$(dirname "$0")" && pwd)"
LABEL="com.starfysh.tiktokrecipes"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$DIR/runs/hourly.log"
mkdir -p "$DIR/runs"
# TikTok share links carry "&", which is invalid raw XML.
xml() { printf '%s' "$1" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g'; }

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/sh</string>
    <string>-c</string>
    <string>git -C "\$0" pull --ff-only --quiet origin main || echo "\$(date '+%Y-%m-%d %H:%M:%S') git pull failed, running local code"; exec "\$1" "\$0/tiktok_recipes.py" "\$2"</string>
    <string>$(xml "$DIR")</string>
    <string>$(python3 -c "import sys; print(sys.executable)")</string>
    <string>$(xml "$URL")</string>
  </array>
  <key>WorkingDirectory</key><string>$(xml "$DIR")</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>PYTHONUNBUFFERED</key><string>1</string>
  </dict>
  <key>StartInterval</key><integer>3600</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$(xml "$LOG")</string>
  <key>StandardErrorPath</key><string>$(xml "$LOG")</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Installed $LABEL. Pulls main and runs now and every hour. Log: $LOG"
