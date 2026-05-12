#!/usr/bin/env bash
# Runs the commit tracker every 6 hours. Keep this alive in tmux/screen.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$SCRIPT_DIR/../commit_reports/cron.log"
INTERVAL=$((6 * 60 * 60))  # 6 hours in seconds

mkdir -p "$(dirname "$LOG")"

echo "[$(date -u '+%Y-%m-%d %H:%M UTC')] Tracker started (interval: 6h)" | tee -a "$LOG"

while true; do
    echo "[$(date -u '+%Y-%m-%d %H:%M UTC')] Running..." | tee -a "$LOG"
    python3 "$SCRIPT_DIR/track_commits.py" 2>&1 | tee -a "$LOG"
    echo "[$(date -u '+%Y-%m-%d %H:%M UTC')] Next run in 6 hours." | tee -a "$LOG"
    sleep "$INTERVAL"
done
