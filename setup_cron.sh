#!/usr/bin/env bash
# Installs a cron job that runs github_commit_tracker.py every 6 hours.
# Run once with:  bash setup_cron.sh
#
# Prerequisites:
#   export GITHUB_TOKEN=<your_token>   (add to ~/.bashrc / ~/.profile for persistence)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$(command -v python3)"
TRACKER="$SCRIPT_DIR/github_commit_tracker.py"
LOG_OUT="$SCRIPT_DIR/tracker_cron.log"

# Cron line: run at minute 0 of hours 0,6,12,18 every day
CRON_LINE="0 0,6,12,18 * * * GITHUB_TOKEN=\"\$GITHUB_TOKEN\" $PYTHON $TRACKER >> $LOG_OUT 2>&1"

# Add only if not already present
( crontab -l 2>/dev/null | grep -qF "$TRACKER" ) && {
    echo "Cron job already installed."
    exit 0
}

( crontab -l 2>/dev/null; echo "$CRON_LINE" ) | crontab -
echo "Cron job installed. Runs at 00:00, 06:00, 12:00, 18:00 UTC."
echo "Output logged to: $LOG_OUT"
echo ""
echo "To remove it later run:  crontab -e  and delete the line containing github_commit_tracker.py"
