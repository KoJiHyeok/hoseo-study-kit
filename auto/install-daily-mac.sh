#!/bin/bash
# 매일 07:40 자동 점검을 LaunchAgent 로 등록 (맥).
# 끄기: launchctl bootout gui/$(id -u)/com.hoseostudykit.daily
# 즉시 실행: launchctl kickstart gui/$(id -u)/com.hoseostudykit.daily
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
chmod +x "$ROOT/auto/daily-check.sh"
AGENT="$HOME/Library/LaunchAgents/com.hoseostudykit.daily.plist"
cat > "$AGENT" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.hoseostudykit.daily</string>
  <key>ProgramArguments</key><array><string>/bin/zsh</string><string>$ROOT/auto/daily-check.sh</string></array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>40</integer></dict>
  <key>StandardErrorPath</key><string>$ROOT/auto/launchd.err</string>
</dict></plist>
PL
launchctl bootout "gui/$(id -u)/com.hoseostudykit.daily" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$AGENT"
echo "OK: 매일 07:40 자동 점검 등록 — $AGENT"
