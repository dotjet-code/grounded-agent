#!/bin/bash
# Emergency stop for the persona autopost agent. Safe to run repeatedly.
#
#   1. Creates data/STOP        -> SafetyGuard blocks every future run (exit 2)
#   2. Boots out the launchd job -> no future runs are scheduled at all
#
# Restore with scripts/resume_autopost.sh
set -euo pipefail
cd "$(dirname "$0")/.."

PLIST="$HOME/Library/LaunchAgents/com.grounded-agent.persona-autopost.plist"
LABEL="com.grounded-agent.persona-autopost"
DOMAIN="gui/$(id -u)"

date -u +"%Y-%m-%dT%H:%M:%SZ kill switch engaged" >> data/logs/safety-alerts.log 2>/dev/null || true
touch data/STOP
echo "STOP file created: data/STOP"

# NOTE: query the gui domain directly. `launchctl list LABEL` fails from
# non-gui shells even when the job is loaded (learned in the 2026-08-08 drill).
if launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
  launchctl bootout "$DOMAIN" "$PLIST" 2>/dev/null || launchctl unload "$PLIST"
  echo "launchd job booted out: $LABEL"
else
  echo "launchd job was not loaded: $LABEL"
fi

echo "--- verification ---"
ls -la data/STOP
if launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
  echo "!! FAILED: job still loaded"
  exit 1
fi
echo "OK: job absent from $DOMAIN"
echo "Agent is stopped. To resume: scripts/resume_autopost.sh"
