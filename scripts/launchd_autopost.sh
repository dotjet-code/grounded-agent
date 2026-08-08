#!/bin/bash
# launchd wrapper for com.grounded-agent.persona-autopost
# Secrets live in data/.env (chmod 600, gitignored) — not in the plist.
set -euo pipefail
cd '/Users/nakajima/projects/grounded-agent'
set -a
. ./data/.env
set +a
exec '/Users/nakajima/projects/grounded-agent/.venv/bin/python' -m src.persona autopost-once --policy data/posting_policy.json
