#!/usr/bin/env bash
# Start the GitHub commit monitor daemon in the background.
# Usage: GITHUB_TOKEN=ghp_xxx ./scripts/start_monitor.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/daemon.pid"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Monitor already running (PID $(cat "$PID_FILE"))."
    exit 0
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "ERROR: GITHUB_TOKEN environment variable must be set."
    echo "Usage: GITHUB_TOKEN=ghp_xxx ./scripts/start_monitor.sh"
    exit 1
fi

nohup python3 "$SCRIPT_DIR/commit_monitor_daemon.py" \
    >> "$SCRIPT_DIR/daemon.log" 2>&1 &

echo "Monitor started (PID $!)."
echo "Logs: $SCRIPT_DIR/daemon.log"
echo "Commit log: $(dirname "$SCRIPT_DIR")/commit_log.md"
