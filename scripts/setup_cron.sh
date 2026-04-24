#!/usr/bin/env bash
# Sets up a cron job to run github_commit_tracker.py every 6 hours.
# Run this script once to install the cron job.
#
# Usage:
#   GITHUB_TOKEN=ghp_... ./scripts/setup_cron.sh
#   GITHUB_TOKEN=ghp_... GITHUB_REPOS="owner/repo1,owner/repo2" ./scripts/setup_cron.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
TRACKER="$SCRIPT_DIR/github_commit_tracker.py"
LOG_FILE="$REPO_ROOT/commit_reports/tracker.log"
REPORT_FILE="$REPO_ROOT/commit_reports/report.md"

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "Error: GITHUB_TOKEN is not set."
  echo "Usage: GITHUB_TOKEN=ghp_... ./scripts/setup_cron.sh"
  exit 1
fi

GITHUB_REPOS="${GITHUB_REPOS:-}"

# Build the cron environment line and command
CRON_ENV="GITHUB_TOKEN=$GITHUB_TOKEN"
if [[ -n "$GITHUB_REPOS" ]]; then
  CRON_ENV="$CRON_ENV GITHUB_REPOS=$GITHUB_REPOS"
fi
CRON_ENV="$CRON_ENV REPORT_FILE=$REPORT_FILE"

CRON_CMD="$CRON_ENV python3 $TRACKER >> $LOG_FILE 2>&1"

# Run at minute 0, every 6 hours: 00:00, 06:00, 12:00, 18:00
CRON_SCHEDULE="0 */6 * * *"

CRON_LINE="$CRON_SCHEDULE $CRON_CMD"

# Add to crontab if not already present
EXISTING=$(crontab -l 2>/dev/null || true)
if echo "$EXISTING" | grep -qF "$TRACKER"; then
  echo "Cron job already exists. Replacing..."
  EXISTING=$(echo "$EXISTING" | grep -vF "$TRACKER")
fi

(echo "$EXISTING"; echo "$CRON_LINE") | crontab -

echo "Cron job installed:"
echo "  Schedule : every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)"
echo "  Script   : $TRACKER"
echo "  Report   : $REPORT_FILE"
echo "  Log      : $LOG_FILE"
echo ""
echo "To view current crontab: crontab -l"
echo "To remove the job:       crontab -l | grep -vF '$TRACKER' | crontab -"
