#!/usr/bin/env bash
# Cron wrapper for track_commits.py
# Set GITHUB_TOKEN here or in a ~/.env file

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../logs"
mkdir -p "$LOG_DIR"

# Load token from ~/.env if not already set
if [[ -z "${GITHUB_TOKEN:-}" && -f "$HOME/.env" ]]; then
    # shellcheck disable=SC1090
    source "$HOME/.env"
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
    echo "$(date -u): ERROR — GITHUB_TOKEN not set" >> "$LOG_DIR/tracker.log"
    exit 1
fi

python3 "$SCRIPT_DIR/track_commits.py" \
    --hours 6 \
    --user peak-flow \
    --output "$SCRIPT_DIR/../commit_log.md" \
    >> "$LOG_DIR/tracker.log" 2>&1

echo "$(date -u): run complete" >> "$LOG_DIR/tracker.log"
