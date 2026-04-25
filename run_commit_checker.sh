#!/usr/bin/env bash
# Runs check_github_commits.py every 6 hours in the background.
# Usage: bash run_commit_checker.sh [start|stop|status]
# Requires: GITHUB_TOKEN env var set before calling start.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDFILE="$SCRIPT_DIR/.commit_checker.pid"
LOGFILE="$SCRIPT_DIR/cron.log"
INTERVAL=$((6 * 3600))  # 6 hours in seconds

_run_loop() {
    while true; do
        echo "[$(date -u '+%Y-%m-%d %H:%M UTC')] Running commit check..." >> "$LOGFILE"
        python3 "$SCRIPT_DIR/check_github_commits.py" >> "$LOGFILE" 2>&1
        sleep "$INTERVAL"
    done
}

case "${1:-start}" in
    start)
        if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
            echo "Already running (PID $(cat "$PIDFILE"))."
            exit 0
        fi
        if [ -z "$GITHUB_TOKEN" ]; then
            echo "ERROR: GITHUB_TOKEN is not set. Export it first:"
            echo "  export GITHUB_TOKEN=your_token_here"
            exit 1
        fi
        export GITHUB_TOKEN
        nohup bash -c "$(declare -f _run_loop); _run_loop" >> "$LOGFILE" 2>&1 &
        echo $! > "$PIDFILE"
        echo "Started (PID $!). Logs: $LOGFILE"
        echo "First run in a moment — subsequent runs every 6 hours."
        # Trigger an immediate first run
        sleep 2
        python3 "$SCRIPT_DIR/check_github_commits.py" >> "$LOGFILE" 2>&1 &
        ;;
    stop)
        if [ -f "$PIDFILE" ]; then
            PID=$(cat "$PIDFILE")
            kill "$PID" 2>/dev/null && echo "Stopped (PID $PID)." || echo "Process not found."
            rm -f "$PIDFILE"
        else
            echo "Not running."
        fi
        ;;
    status)
        if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
            echo "Running (PID $(cat "$PIDFILE"))."
        else
            echo "Not running."
        fi
        ;;
    *)
        echo "Usage: $0 [start|stop|status]"
        ;;
esac
