#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.daemon.pid"

if [[ ! -f "$PID_FILE" ]]; then
    echo "No PID file found — daemon may not be running."
    exit 0
fi

PID="$(cat "$PID_FILE")"
if kill -0 "$PID" 2>/dev/null; then
    kill "$PID" && echo "Daemon (PID $PID) stopped."
else
    echo "Process $PID not found (already stopped)."
fi
rm -f "$PID_FILE"
