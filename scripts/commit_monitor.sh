#!/usr/bin/env bash
# Persistent daemon: runs check_commits.sh every 6 hours.
# Start with: nohup ./commit_monitor.sh &
# Stop with:  kill $(cat /home/user/peaktrack/scripts/commit_monitor.pid)

set -euo pipefail

PID_FILE="/home/user/peaktrack/scripts/commit_monitor.pid"
LOG_FILE="/home/user/peaktrack/scripts/commit_monitor.log"
CHECK_SCRIPT="$(dirname "$0")/check_commits.sh"
INTERVAL_SECONDS=$((6 * 60 * 60))   # 6 hours

# Prevent duplicate instances
if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Monitor already running (PID $(cat "$PID_FILE")). Exiting." >&2
  exit 1
fi

echo $$ > "$PID_FILE"
trap 'rm -f "$PID_FILE"; exit 0' INT TERM EXIT

log() { echo "[$(date -u +"%Y-%m-%d %H:%M UTC")] $*" | tee -a "$LOG_FILE"; }

log "Commit monitor started (PID $$, interval=${INTERVAL_SECONDS}s)"

while true; do
  log "Running commit check..."
  if bash "$CHECK_SCRIPT" >> "$LOG_FILE" 2>&1; then
    log "Check completed successfully."
  else
    log "Check failed (exit $?). Will retry at next interval."
  fi
  log "Sleeping ${INTERVAL_SECONDS}s until next check..."
  sleep "$INTERVAL_SECONDS"
done
