#!/usr/bin/env bash
# Runs check-commits.py every 6 hours. Start with: nohup ./commit-watcher.sh &
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$SCRIPT_DIR/check-commits.log"
INTERVAL=21600  # 6 hours in seconds

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] commit-watcher started (interval=${INTERVAL}s)" | tee -a "$LOG"

while true; do
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Running commit check..." >> "$LOG"
    python3 "$SCRIPT_DIR/check-commits.py" >> "$LOG" 2>&1 && \
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Done." >> "$LOG" || \
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ERROR: check-commits.py failed (exit $?)" >> "$LOG"
    sleep "$INTERVAL"
done
