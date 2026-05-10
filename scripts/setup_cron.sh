#!/usr/bin/env bash
# Sets up a cron job to run github_commit_tracker.py every 6 hours.
# Run once: bash scripts/setup_cron.sh
#
# Required: set GITHUB_TOKEN before running this script.
# Optional: set GITHUB_REPOS or GITHUB_ORGS to scope which repos are checked.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TRACKER="$SCRIPT_DIR/github_commit_tracker.py"
REPORT="$PROJECT_DIR/commit_reports/github_commits.md"
LOG="$PROJECT_DIR/commit_reports/tracker.log"
PYTHON="${PYTHON:-$(command -v python3)}"

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "Error: GITHUB_TOKEN is not set. Export it before running this script."
  exit 1
fi

# Build the cron environment block (cron doesn't inherit shell env)
ENV_LINE="GITHUB_TOKEN=$GITHUB_TOKEN"

if [[ -n "${GITHUB_REPOS:-}" ]]; then
  ENV_LINE="$ENV_LINE
GITHUB_REPOS=$GITHUB_REPOS"
fi

if [[ -n "${GITHUB_ORGS:-}" ]]; then
  ENV_LINE="$ENV_LINE
GITHUB_ORGS=$GITHUB_ORGS"
fi

CRON_CMD="$PYTHON $TRACKER --output $REPORT >> $LOG 2>&1"
# Run at minute 0, every 6 hours: 00:00, 06:00, 12:00, 18:00
CRON_SCHEDULE="0 */6 * * *"
CRON_LINE="$CRON_SCHEDULE $CRON_CMD"
MARKER="# github-commit-tracker"

# Read existing crontab (ignore error if empty)
EXISTING_CRON="$(crontab -l 2>/dev/null || true)"

# Remove any previous entry for this tracker
CLEANED_CRON="$(echo "$EXISTING_CRON" | grep -v "$MARKER" | grep -v "github_commit_tracker" || true)"

NEW_CRON="$(printf '%s\n%s\n%s %s\n' "$CLEANED_CRON" "$ENV_LINE" "$CRON_SCHEDULE" "$CRON_CMD $MARKER")"

echo "$NEW_CRON" | crontab -

echo "Cron job installed. It will run every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)."
echo "Report will be saved to: $REPORT"
echo "Logs will be written to:  $LOG"
echo ""
echo "To run immediately:"
echo "  GITHUB_TOKEN=$GITHUB_TOKEN $PYTHON $TRACKER --output $REPORT"
echo ""
echo "To remove the cron job:"
echo "  crontab -l | grep -v github_commit_tracker | crontab -"
