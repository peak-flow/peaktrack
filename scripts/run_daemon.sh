#!/usr/bin/env bash
# Run check_commits.py every 6 hours in the background.
# Usage: ./run_daemon.sh [start|stop|status]
#   start  — launch daemon (idempotent)
#   stop   — kill running daemon
#   status — show whether daemon is running

PIDFILE="$(dirname "$0")/daemon.pid"
LOGFILE="$(dirname "$0")/cron.log"
SCRIPT="$(dirname "$0")/check_commits.py"
INTERVAL=$((6 * 60 * 60))  # 6 hours in seconds

start() {
    if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "Daemon already running (PID $(cat "$PIDFILE"))"
        return
    fi
    nohup bash -c "
        while true; do
            echo \"[$(date -u '+%Y-%m-%d %H:%M UTC')] Running check...\" >> \"$LOGFILE\"
            python3 \"$SCRIPT\" >> \"$LOGFILE\" 2>&1
            sleep $INTERVAL
        done
    " >/dev/null 2>&1 &
    echo $! > "$PIDFILE"
    echo "Daemon started (PID $!). Log: $LOGFILE"
}

stop() {
    if [[ -f "$PIDFILE" ]]; then
        PID=$(cat "$PIDFILE")
        if kill "$PID" 2>/dev/null; then
            echo "Stopped daemon (PID $PID)"
        else
            echo "PID $PID not found (already stopped?)"
        fi
        rm -f "$PIDFILE"
    else
        echo "No PID file found — daemon may not be running"
    fi
}

status() {
    if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "Running (PID $(cat "$PIDFILE"))"
    else
        echo "Not running"
    fi
}

case "${1:-start}" in
    start)  start  ;;
    stop)   stop   ;;
    status) status ;;
    *)      echo "Usage: $0 [start|stop|status]" ;;
esac
