#!/usr/bin/env bash
# Background daemon: runs check_commits.sh every 6 hours.
# Start with: nohup /home/user/peaktrack/commit_watcher.sh &

SCRIPT_DIR="$(dirname "$0")"
INTERVAL=21600  # 6 hours in seconds

echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] commit_watcher started (PID $$)"

while true; do
  "$SCRIPT_DIR/check_commits.sh" 2>&1
  echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] sleeping ${INTERVAL}s until next check"
  sleep "$INTERVAL"
done
