#!/bin/bash
# Runs check_commits.sh immediately, then every 6 hours in the background.
# Usage:  ./start_commit_watcher.sh [--token YOUR_TOKEN]
#
# Token precedence: --token arg > GITHUB_TOKEN env var > .env file

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK_SCRIPT="$SCRIPT_DIR/check_commits.sh"
ENV_FILE="$SCRIPT_DIR/.env"
LOG_FILE="$SCRIPT_DIR/cron.log"
PID_FILE="$SCRIPT_DIR/.watcher.pid"

# Parse --token argument
while [[ $# -gt 0 ]]; do
  case "$1" in
    --token) export GITHUB_TOKEN="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

# Load .env if token not already set
if [[ -z "${GITHUB_TOKEN:-}" && -f "$ENV_FILE" ]]; then
  # shellcheck source=/dev/null
  source "$ENV_FILE"
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "ERROR: Provide GITHUB_TOKEN via env, .env file, or --token flag." >&2
  exit 1
fi

# Kill any existing watcher
if [[ -f "$PID_FILE" ]]; then
  OLD_PID=$(cat "$PID_FILE")
  kill "$OLD_PID" 2>/dev/null && echo "Stopped previous watcher (PID $OLD_PID)"
fi

loop() {
  echo $$ > "$PID_FILE"
  echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Watcher started (PID $$, every 6h)" | tee -a "$LOG_FILE"
  while true; do
    bash "$CHECK_SCRIPT" 2>&1 | tee -a "$LOG_FILE"
    sleep 21600  # 6 hours
  done
}

# Detach and run in background
nohup bash -c "$(declare -f loop); GITHUB_TOKEN='$GITHUB_TOKEN' loop" >> "$LOG_FILE" 2>&1 &
WATCHER_PID=$!
echo "$WATCHER_PID" > "$PID_FILE"
echo "Watcher started in background (PID $WATCHER_PID)."
echo "Logs:   $LOG_FILE"
echo "Report: $SCRIPT_DIR/commit_report.md"
echo ""
echo "To stop: kill \$(cat $PID_FILE)"
