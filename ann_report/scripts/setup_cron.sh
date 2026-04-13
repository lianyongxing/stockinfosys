#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLIST_NAME="com.quant.ann-report-daily.plist"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME"
PYTHON_BIN=$(which python3 || which python)
LOG_DIR="$REPO_DIR/logs"
mkdir -p "$LOG_DIR"

PLIST_CONTENT="<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
<dict>
    <key>Label</key>
    <string>com.quant.ann-report-daily</string>
    <key>ProgramArguments</key>
    <array>
        <string>$SCRIPT_DIR/../daily.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$REPO_DIR</string>
    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Hour</key>
            <integer>23</integer>
            <key>Minute</key>
            <integer>30</integer>
        </dict>
    </array>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/daily.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/daily.err</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>"

echo "$PLIST_CONTENT" > "$PLIST_PATH"
chmod 644 "$PLIST_PATH"

launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo "定时任务已设置: $PLIST_PATH"
echo "每天 23:30 自动采集+合并+推送"
echo "日志: $LOG_DIR/daily.log"
echo ""
echo "卸载: launchctl unload $PLIST_PATH && rm $PLIST_PATH"