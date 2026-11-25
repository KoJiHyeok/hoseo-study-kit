#!/bin/bash
# ~/Applications/할일.app 빌드 — 크롬과 분리된 네이티브 창 (Swift WKWebView 껍데기 + app.py 서버)
set -e
DASH="$(cd "$(dirname "$0")" && pwd)"
PY="$(command -v python3)"
APP="$HOME/Applications/할일.app"
TMP="$(mktemp -d)"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
swiftc -O -swift-version 5 -target "$(uname -m)-apple-macos14.0" -o "$APP/Contents/MacOS/HoseoDash" "$DASH/mac/main.swift" -framework Cocoa -framework WebKit

# 아이콘 (PIL 있는 파이썬이 있을 때만)
ICONPY=""; for p in "$HOME/.venvs/stt/bin/python" "$PY"; do "$p" -c "import PIL" 2>/dev/null && ICONPY="$p" && break; done
if [ -n "$ICONPY" ]; then
  "$ICONPY" "$DASH/mac/make_icon.py" "$TMP/icon.png"
  mkdir "$TMP/i.iconset"
  for s in 16 32 128 256 512; do
    sips -z $s $s "$TMP/icon.png" --out "$TMP/i.iconset/icon_${s}x${s}.png" >/dev/null
    sips -z $((s*2)) $((s*2)) "$TMP/icon.png" --out "$TMP/i.iconset/icon_${s}x${s}@2x.png" >/dev/null
  done
  iconutil -c icns "$TMP/i.iconset" -o "$APP/Contents/Resources/icon.icns"
fi

cat > "$APP/Contents/Info.plist" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>할일</string>
  <key>CFBundleDisplayName</key><string>할일</string>
  <key>CFBundleIdentifier</key><string>com.hoseostudykit.dash</string>
  <key>CFBundleExecutable</key><string>HoseoDash</string>
  <key>CFBundleIconFile</key><string>icon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSMinimumSystemVersion</key><string>14.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSAppTransportSecurity</key><dict><key>NSAllowsLocalNetworking</key><true/></dict>
  <key>HoseoDash</key><string>$DASH</string>
  <key>HoseoPython</key><string>$PY</string>
</dict></plist>
PL
rm -rf "$TMP"
touch "$APP"

# 로그인 시 자동 실행 (LaunchAgent). 끄기: launchctl bootout gui/$(id -u)/com.hoseostudykit.dash
AGENT="$HOME/Library/LaunchAgents/com.hoseostudykit.dash.plist"
if [ ! -f "$AGENT" ]; then
  cat > "$AGENT" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.hoseostudykit.dash</string>
  <key>ProgramArguments</key><array><string>/usr/bin/open</string><string>-a</string><string>$APP</string></array>
  <key>RunAtLoad</key><true/>
</dict></plist>
PL
  launchctl bootstrap "gui/$(id -u)" "$AGENT" && echo "자동 실행 등록: $AGENT"
fi
echo "OK: $APP"
