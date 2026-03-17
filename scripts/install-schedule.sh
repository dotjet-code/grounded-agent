#!/usr/bin/env bash
# Install/uninstall the persona autopost launchd schedule.
#
# Usage:
#   ./scripts/install-schedule.sh install          # load plist (4h interval)
#   ./scripts/install-schedule.sh install-test     # load plist (5min interval for testing)
#   ./scripts/install-schedule.sh uninstall        # unload plist
#   ./scripts/install-schedule.sh status           # check if loaded
#
# Prerequisites:
#   - Environment variables must be set in data/.env
#   - Create data/.env with your API keys (never commit this file)

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_SRC="${PROJECT_DIR}/scripts/persona-autopost.plist"
PLIST_DST="${HOME}/Library/LaunchAgents/com.grounded-agent.persona-autopost.plist"
LABEL="com.grounded-agent.persona-autopost"
LOG_DIR="${PROJECT_DIR}/data/logs"
ENV_FILE="${PROJECT_DIR}/data/.env"

ensure_logs_dir() {
    mkdir -p "${LOG_DIR}"
}

load_env_into_plist() {
    # Read data/.env and inject into the plist's EnvironmentVariables
    if [[ ! -f "${ENV_FILE}" ]]; then
        echo "Warning: ${ENV_FILE} not found. LaunchAgent will lack API keys."
        echo "Create it with your keys: ANTHROPIC_API_KEY, X_API_KEY, etc."
        return
    fi

    # Build a temp plist with env vars injected
    local tmp_plist
    tmp_plist=$(mktemp)
    cp "${PLIST_SRC}" "${tmp_plist}"

    # Replace the commented-out EnvironmentVariables with real ones
    local env_xml="<dict>"
    while IFS='=' read -r key value; do
        [[ -z "$key" || "$key" == \#* ]] && continue
        value="${value%\"}"
        value="${value#\"}"
        env_xml="${env_xml}<key>${key}</key><string>${value}</string>"
    done < "${ENV_FILE}"
    env_xml="${env_xml}</dict>"

    # Use Python for reliable XML replacement
    python3 -c "
import re, sys
content = open('${tmp_plist}').read()
# Replace the EnvironmentVariables dict
content = re.sub(
    r'<key>EnvironmentVariables</key>\s*<dict>.*?</dict>',
    '<key>EnvironmentVariables</key>${env_xml}',
    content, flags=re.DOTALL
)
open('${PLIST_DST}', 'w').write(content)
"
    rm "${tmp_plist}"
}

cmd_install() {
    local interval="${1:-14400}"
    ensure_logs_dir

    # Copy and configure plist
    cp "${PLIST_SRC}" "${PLIST_DST}"

    # Set interval
    sed -i '' "s|<integer>[0-9]*</integer>|<integer>${interval}</integer>|" "${PLIST_DST}"

    # Inject env vars if available
    load_env_into_plist

    # Load
    launchctl load "${PLIST_DST}" 2>/dev/null || true
    echo "Loaded: ${LABEL} (interval: ${interval}s)"
    echo "Logs: ${LOG_DIR}/autopost.{stdout,stderr}.log"
}

cmd_uninstall() {
    launchctl unload "${PLIST_DST}" 2>/dev/null || true
    rm -f "${PLIST_DST}"
    echo "Unloaded: ${LABEL}"
}

cmd_status() {
    if launchctl list "${LABEL}" &>/dev/null; then
        echo "Running: ${LABEL}"
        launchctl list "${LABEL}"
    else
        echo "Not loaded: ${LABEL}"
    fi
}

case "${1:-}" in
    install)
        cmd_install 14400  # 4 hours
        ;;
    install-test)
        cmd_install 300    # 5 minutes
        ;;
    uninstall)
        cmd_uninstall
        ;;
    status)
        cmd_status
        ;;
    *)
        echo "Usage: $0 {install|install-test|uninstall|status}"
        exit 1
        ;;
esac
