#!/bin/bash
# Background daemon: runs the commit tracker every 6 hours.
# Usage:
#   Start in background: nohup ./scripts/commit_tracker_daemon.sh &
#   Stop:                kill $(cat /tmp/commit_tracker.pid)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="/tmp/commit_tracker.pid"
LOG="$SCRIPT_DIR/../commit_tracker.log"
INTERVAL=$((6 * 60 * 60))  # 6 hours in seconds

echo $$ > "$PID_FILE"
echo "[$(date -u '+%Y-%m-%d %H:%M UTC')] Daemon started (PID $$, interval=${INTERVAL}s)" >> "$LOG"

# Load token if present
SECRETS="$SCRIPT_DIR/../.github_token"
if [ -f "$SECRETS" ]; then
    # shellcheck source=/dev/null
    source "$SECRETS"
fi

cleanup() {
    echo "[$(date -u '+%Y-%m-%d %H:%M UTC')] Daemon stopped" >> "$LOG"
    rm -f "$PID_FILE"
}
trap cleanup EXIT

while true; do
    python3 "$SCRIPT_DIR/github_commit_tracker.py" >> "$LOG" 2>&1
    echo "[$(date -u '+%Y-%m-%d %H:%M UTC')] Next run in ${INTERVAL}s" >> "$LOG"
    sleep "$INTERVAL"
done
