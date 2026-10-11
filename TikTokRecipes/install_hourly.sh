#!/bin/bash
# Install a launchd agent that runs tiktok_recipes.py every hour, which also publishes the site.
# Usage: TikTokRecipes/install_hourly.sh '<collection-url>'
# Remove: launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.starfysh.tiktokrecipes.plist
set -euo pipefail

URL="${1:?usage: install_hourly.sh <collection-url>}"
DIR="$(cd "$(dirname "$0")" && pwd)"
LABEL="com.starfysh.tiktokrecipes"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$DIR/runs/hourly.log"
mkdir -p "$DIR/runs"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$(command -v python3)</string>
    <string>$DIR/tiktok_recipes.py</string>
    <string>$URL</string>
  </array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>PYTHONUNBUFFERED</key><string>1</string>
  </dict>
  <key>StartInterval</key><integer>3600</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Installed $LABEL. Runs now and every hour. Log: $LOG"
