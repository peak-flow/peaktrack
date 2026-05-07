#!/usr/bin/env bash
# Sets up a cron job to run check_commits.py every 6 hours.
# Run once: bash setup_cron.sh
# Requirements: python3, a GITHUB_TOKEN in your environment or ~/.env

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$(command -v python3)"
LOG="$SCRIPT_DIR/commit_tracker.log"

# ── Edit these if needed ───────────────────────────────────────────────────────
REPOS="peak-flow/peaktrack"          # comma-separated owner/repo pairs
OUTPUT="$SCRIPT_DIR/commit_report.md"
HOURS=6
# ──────────────────────────────────────────────────────────────────────────────

CRON_ENV="GITHUB_TOKEN=\$GITHUB_TOKEN COMMIT_TRACKER_REPOS=\"$REPOS\" COMMIT_TRACKER_OUTPUT=\"$OUTPUT\" COMMIT_TRACKER_HOURS=$HOURS"
CRON_CMD="$PYTHON $SCRIPT_DIR/check_commits.py >> $LOG 2>&1"

# Run at minute 0 every 6 hours: 00:00, 06:00, 12:00, 18:00
CRON_LINE="0 */6 * * * $CRON_ENV $CRON_CMD"

# Add to crontab if not already present
( crontab -l 2>/dev/null | grep -v "check_commits.py"; echo "$CRON_LINE" ) | crontab -

echo "Cron job installed:"
echo "  $CRON_LINE"
echo ""
echo "Make sure GITHUB_TOKEN is exported in your shell profile (~/.bashrc or ~/.zshrc)."
echo "Logs will be written to: $LOG"
echo "Reports will be appended to: $OUTPUT"
echo ""
echo "To remove the cron job run:"
echo "  crontab -l | grep -v 'check_commits.py' | crontab -"
