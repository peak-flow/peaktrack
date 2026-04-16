#!/usr/bin/env bash
# setup_cron.sh — Install a cron job that runs github_commit_tracker.py every 6 hours.
#
# Usage:
#   export GITHUB_TOKEN="ghp_your_token_here"
#   bash scripts/setup_cron.sh
#
# To remove the cron job later:
#   crontab -l | grep -v 'github_commit_tracker' | crontab -

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TRACKER="$SCRIPT_DIR/github_commit_tracker.py"
OUTPUT="$REPO_ROOT/commit_log.md"
LOG="$REPO_ROOT/scripts/cron.log"
PYTHON="${PYTHON:-$(command -v python3 || echo python)}"

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
    echo "Error: GITHUB_TOKEN is not set. Export it before running this script."
    echo "  export GITHUB_TOKEN=\"ghp_your_token_here\""
    exit 1
fi

# Build the cron line: run at minutes 0 of hours 0,6,12,18 every day
CRON_JOB="0 0,6,12,18 * * * GITHUB_TOKEN=\"${GITHUB_TOKEN}\" ${PYTHON} ${TRACKER} --hours 6 --output ${OUTPUT} >> ${LOG} 2>&1"

# Remove any existing entry for this tracker, then add the new one
( crontab -l 2>/dev/null | grep -v 'github_commit_tracker' ; echo "$CRON_JOB" ) | crontab -

echo "Cron job installed successfully."
echo ""
echo "Schedule : every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)"
echo "Output   : $OUTPUT"
echo "Cron log : $LOG"
echo ""
echo "Current crontab:"
crontab -l | grep 'github_commit_tracker' || true
echo ""
echo "To run immediately and verify:"
echo "  GITHUB_TOKEN=\"\$GITHUB_TOKEN\" python3 $TRACKER --hours 6 --output $OUTPUT"
