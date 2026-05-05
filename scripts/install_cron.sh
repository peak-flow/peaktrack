#!/usr/bin/env bash
# Installs a cron job that runs github_commit_tracker.py every 6 hours.
# Run this once: bash scripts/install_cron.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRACKER="$SCRIPT_DIR/github_commit_tracker.py"
LOG_FILE="$SCRIPT_DIR/../commit_reports/tracker.log"

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "ERROR: Set the GITHUB_TOKEN environment variable before running this script."
  exit 1
fi

# Build the cron line (runs at minute 0 of hours 0,6,12,18)
CRON_LINE="0 0,6,12,18 * * * GITHUB_TOKEN=${GITHUB_TOKEN} /usr/bin/env python3 ${TRACKER} >> ${LOG_FILE} 2>&1"

# Remove any existing entry for this tracker, then add the new one
( crontab -l 2>/dev/null | grep -v "$TRACKER" ; echo "$CRON_LINE" ) | crontab -

echo "Cron job installed:"
echo "  $CRON_LINE"
echo ""
echo "Logs will appear in: $LOG_FILE"
echo "Reports will appear in: $(dirname "$LOG_FILE")/commits.md"
