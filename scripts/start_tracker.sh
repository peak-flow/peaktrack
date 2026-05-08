#!/bin/bash
# Starts the commit tracker as a background daemon.
# Logs to /home/user/peaktrack/scripts/tracker.log
#
# Usage:
#   ./start_tracker.sh              # uses GITHUB_TOKEN from env
#   GITHUB_TOKEN=ghp_xxx ./start_tracker.sh
#   GITHUB_OWNER=myorg ./start_tracker.sh
#
# Stop with: kill $(cat /home/user/peaktrack/scripts/tracker.pid)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/tracker.log"
PID_FILE="$SCRIPT_DIR/tracker.pid"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Tracker already running (PID $(cat "$PID_FILE")). Stop it first:"
    echo "  kill \$(cat $PID_FILE)"
    exit 1
fi

export GITHUB_TOKEN="${GITHUB_TOKEN:-}"
export GITHUB_OWNER="${GITHUB_OWNER:-peak-flow}"

nohup python3 "$SCRIPT_DIR/commit_tracker.py" >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "Tracker started (PID $!)"
echo "  Log:    $LOG_FILE"
echo "  Report: $(dirname "$SCRIPT_DIR")/commit_log.md"
echo "  Stop:   kill \$(cat $PID_FILE)"
