#!/usr/bin/env bash
# Background loop: checks GitHub every 6 hours via GitHub API.
# Run once to start; it will keep running until the process is killed.
# Usage: GITHUB_TOKEN=ghp_xxx ./run_commit_watcher.sh &
#        or set ~/.github_token first

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[$(date -u)] Commit watcher started (PID $$). Checks every 6 hours."
echo "$$" > "$SCRIPT_DIR/.watcher.pid"

while true; do
  bash "$SCRIPT_DIR/check_commits.sh"
  echo "[$(date -u)] Next check in 6 hours..."
  sleep 21600
done
