#!/usr/bin/env bash
# Runs the GitHub commit tracker every 6 hours in the background.
# Usage: bash scripts/run_commit_tracker.sh [start|stop|status]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/commit_tracker.pid"
LOG_FILE="$SCRIPT_DIR/cron.log"
ENV_FILE="$SCRIPT_DIR/../.env"
INTERVAL=$((6 * 3600))  # 6 hours in seconds

_load_env() {
    if [[ -f "$ENV_FILE" ]]; then
        # Export non-comment, non-empty lines
        set -a
        # shellcheck disable=SC1090
        source <(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$')
        set +a
    fi
}

_loop() {
    while true; do
        _load_env
        /usr/local/bin/python3 "$SCRIPT_DIR/check_commits.py" >> "$LOG_FILE" 2>&1
        sleep "$INTERVAL"
    done
}

start() {
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Tracker already running (PID $(cat "$PID_FILE"))."
        return
    fi
    _loop &
    echo $! > "$PID_FILE"
    echo "Commit tracker started (PID $!). Logs: $LOG_FILE"
}

stop() {
    if [[ -f "$PID_FILE" ]]; then
        PID=$(cat "$PID_FILE")
        if kill "$PID" 2>/dev/null; then
            echo "Stopped PID $PID."
        else
            echo "Process not found."
        fi
        rm -f "$PID_FILE"
    else
        echo "Not running."
    fi
}

status() {
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Running (PID $(cat "$PID_FILE"))."
    else
        echo "Not running."
    fi
}

case "${1:-start}" in
    start)  start ;;
    stop)   stop  ;;
    status) status ;;
    *)      echo "Usage: $0 [start|stop|status]" ;;
esac
