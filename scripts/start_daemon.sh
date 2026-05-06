#!/usr/bin/env bash
# Starts the commit checker as a background daemon that runs every 6 hours.
# Usage: ./start_daemon.sh [--hours 6]
# Stop with: kill $(cat /home/user/peaktrack/scripts/.daemon.pid)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.daemon.pid"
LOG_FILE="$(dirname "$SCRIPT_DIR")/commit_check.log"
INTERVAL_HOURS="${1:-6}"
INTERVAL_SECS=$(( INTERVAL_HOURS * 3600 ))

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Daemon already running (PID $(cat "$PID_FILE")). Stop it first:"
    echo "  kill \$(cat $PID_FILE)"
    exit 1
fi

_run() {
    while true; do
        echo "--- $(date -u '+%Y-%m-%d %H:%M UTC') running check ---" >> "$LOG_FILE"
        "$SCRIPT_DIR/run_commit_check.sh" >> "$LOG_FILE" 2>&1
        echo "Next check in ${INTERVAL_HOURS}h…" >> "$LOG_FILE"
        sleep "$INTERVAL_SECS"
    done
}

_run &
DAEMON_PID=$!
echo "$DAEMON_PID" > "$PID_FILE"
echo "Daemon started (PID $DAEMON_PID). Logs: $LOG_FILE"
echo "Stop with: kill \$(cat $PID_FILE)"
