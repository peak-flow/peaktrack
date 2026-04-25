#!/usr/bin/env bash
# Installs a crontab entry that runs check_commits.sh every 6 hours.
# Run once: bash setup_cron.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$SCRIPT_DIR/check_commits.sh"
LOG="$SCRIPT_DIR/check_commits.log"

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "WARNING: GITHUB_TOKEN is not set in this shell."
  echo "The cron job needs it. Add it to your shell profile, e.g.:"
  echo "  echo 'export GITHUB_TOKEN=ghp_...' >> ~/.bashrc"
  echo ""
fi

chmod +x "$SCRIPT"

CRON_LINE="0 */6 * * * GITHUB_TOKEN=${GITHUB_TOKEN:-YOUR_TOKEN_HERE} GITHUB_OWNER=peak-flow OUTPUT_FILE=$SCRIPT_DIR/commit_report.md bash $SCRIPT >> $LOG 2>&1"

# Append only if not already present
( crontab -l 2>/dev/null | grep -qF "$SCRIPT" ) && {
  echo "Cron entry already exists, skipping."
  exit 0
}

( crontab -l 2>/dev/null; echo "$CRON_LINE" ) | crontab -

echo "Cron job installed. It will run at 00:00, 06:00, 12:00, 18:00 UTC each day."
echo "Log file: $LOG"
echo ""
echo "To view the current crontab:  crontab -l"
echo "To remove the job:            crontab -e  (and delete the line)"
