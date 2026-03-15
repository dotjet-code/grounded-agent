#!/bin/bash

COMMAND=$(jq -r '.tool_input.command // ""')

if echo "$COMMAND" | grep -Eq '(^|[[:space:]])rm[[:space:]]+-rf([[:space:]]|$)|(^|[[:space:]])git[[:space:]]+push([[:space:]]|$)'; then
  jq -n '{
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "deny",
      "permissionDecisionReason": "Destructive command blocked by project hook"
    }
  }'
else
  exit 0
fi
