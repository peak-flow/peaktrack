#!/bin/bash
# Wrapper for cron — loads the token from a secrets file if present.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS="$SCRIPT_DIR/../.github_token"

if [ -f "$SECRETS" ]; then
    # File should contain a single line: export GITHUB_TOKEN=ghp_...
    # shellcheck source=/dev/null
    source "$SECRETS"
fi

exec python3 "$SCRIPT_DIR/github_commit_tracker.py" >> "$SCRIPT_DIR/../commit_tracker.log" 2>&1
