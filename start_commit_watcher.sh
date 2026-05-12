#!/usr/bin/env bash
# Runs check_commits.sh every 6 hours in the background.
# Usage: GITHUB_TOKEN=<token> bash start_commit_watcher.sh
# Or:    echo '<token>' > ~/.github_token && bash start_commit_watcher.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INTERVAL=$((6 * 60 * 60))  # 6 hours in seconds
LOG="$SCRIPT_DIR/cron.log"

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  TOKEN_FILE="$HOME/.github_token"
  if [[ -f "$TOKEN_FILE" ]]; then
    export GITHUB_TOKEN
    GITHUB_TOKEN=$(cat "$TOKEN_FILE")
  else
    echo "ERROR: Set GITHUB_TOKEN env var or save token to ~/.github_token" >&2
    exit 1
  fi
fi

run_check() {
  echo "[$(date -u +"%Y-%m-%d %H:%M UTC")] Starting commit check..." >> "$LOG"
  bash "$SCRIPT_DIR/check_commits.sh" >> "$LOG" 2>&1
}

# Run once immediately, then every 6 hours
run_check
while true; do
  sleep "$INTERVAL"
  run_check
done
