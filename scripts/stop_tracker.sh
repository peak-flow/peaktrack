#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SCRIPT_DIR/tracker.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "No PID file found — tracker may not be running."
    exit 0
fi

PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    rm -f "$PID_FILE"
    echo "Tracker stopped (PID $PID)."
else
    echo "No process with PID $PID — already stopped."
    rm -f "$PID_FILE"
fi
