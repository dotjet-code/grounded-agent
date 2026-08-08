#!/bin/bash
# Resume the persona autopost agent after a kill-switch stop.
set -euo pipefail
cd "$(dirname "$0")/.."

PLIST="$HOME/Library/LaunchAgents/com.grounded-agent.persona-autopost.plist"
LABEL="com.grounded-agent.persona-autopost"
DOMAIN="gui/$(id -u)"

rm -f data/STOP
echo "STOP file removed"

if ! launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
  # bootout直後はteardown中でEIOになることがある(2026-08-08訓練で確認)。
  # 少し待ってからのリトライで安定して復帰する。
  launchctl bootstrap "$DOMAIN" "$PLIST" 2>/dev/null || launchctl load "$PLIST" 2>/dev/null || true
  if ! launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
    sleep 3
    launchctl load "$PLIST"
  fi
  echo "launchd job loaded: $LABEL"
else
  echo "launchd job already loaded: $LABEL"
fi

date -u +"%Y-%m-%dT%H:%M:%SZ agent resumed" >> data/logs/safety-alerts.log 2>/dev/null || true
echo "--- verification ---"
launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1 && echo "OK: job loaded in $DOMAIN" || { echo "!! FAILED: not loaded"; exit 1; }
