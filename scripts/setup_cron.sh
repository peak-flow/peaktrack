#!/usr/bin/env bash
# Sets up a cron job to run check_github_commits.py every 6 hours.
# Run once: bash scripts/setup_cron.sh
# Prerequisites: GITHUB_TOKEN and GITHUB_REPOS must be set in your environment.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$(command -v python3)"
LOG="$SCRIPT_DIR/../cron_runner.log"

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set. Export it before running this script."
  exit 1
fi

if [[ -z "${GITHUB_REPOS:-}" ]]; then
  echo "ERROR: GITHUB_REPOS is not set."
  echo "  Example: export GITHUB_REPOS=\"peak-flow/peaktrack,owner/other-repo\""
  exit 1
fi

CRON_LINE="0 */6 * * * GITHUB_TOKEN=\"$GITHUB_TOKEN\" GITHUB_REPOS=\"$GITHUB_REPOS\" $PYTHON $SCRIPT_DIR/check_github_commits.py >> $LOG 2>&1"

# Add to crontab without duplicating
(crontab -l 2>/dev/null | grep -v "check_github_commits"; echo "$CRON_LINE") | crontab -

echo "Cron job installed. It will run every 6 hours."
echo "  Log file: $LOG"
echo "  Commit log: $SCRIPT_DIR/../commit_log.md"
echo ""
echo "To verify: crontab -l"
echo "To remove: crontab -e  (delete the check_github_commits line)"
