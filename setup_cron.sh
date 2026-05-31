#!/usr/bin/env bash
# Installs a cron job that runs the commit tracker every 6 hours.
# Run once: bash setup_cron.sh
# To remove: crontab -e and delete the added line.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$(command -v python3)"
LOG="$SCRIPT_DIR/cron.log"

if [[ -z "$PYTHON" ]]; then
  echo "python3 not found. Install it first." >&2
  exit 1
fi

# Build the cron line — runs at minute 0 every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)
CRON_LINE="0 */6 * * * GITHUB_TOKEN=\"\${GITHUB_TOKEN}\" GITHUB_REPOS=\"peak-flow/peaktrack\" $PYTHON $SCRIPT_DIR/github_commit_tracker.py >> $LOG 2>&1"

# Check if already installed
if crontab -l 2>/dev/null | grep -qF "github_commit_tracker.py"; then
  echo "Cron job already installed."
else
  (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
  echo "Cron job installed. It will run at 00:00, 06:00, 12:00, and 18:00 UTC."
fi

echo ""
echo "Next steps:"
echo "  export GITHUB_TOKEN=<your_personal_access_token>"
echo "  Then run manually to verify: python3 $SCRIPT_DIR/github_commit_tracker.py"
echo "  Results are appended to:     $SCRIPT_DIR/commit_log.md"
echo "  Cron output goes to:         $LOG"
echo ""
echo "To track more repos, set:"
echo "  export GITHUB_REPOS=\"peak-flow/peaktrack,owner2/repo2,owner3/repo3\""
