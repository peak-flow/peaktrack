#!/usr/bin/env bash
# Installs a cron job that runs github_commit_tracker.py every 6 hours.
# Usage:
#   GITHUB_TOKEN=ghp_xxx GITHUB_USER=your-username bash setup_cron.sh
#
# To target specific repos instead of all repos for a user:
#   GITHUB_REPOS="owner/repo1,owner/repo2" bash setup_cron.sh
#
# To remove the cron job later:
#   crontab -l | grep -v 'github_commit_tracker' | crontab -

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRACKER="$SCRIPT_DIR/github_commit_tracker.py"
LOG_FILE="$SCRIPT_DIR/../commit_log.md"
CRON_LOG="$SCRIPT_DIR/../cron_tracker.log"

# Resolve python
PYTHON="$(command -v python3 || command -v python)"
if [[ -z "$PYTHON" ]]; then
  echo "ERROR: python3 not found in PATH" >&2
  exit 1
fi

# Make sure requests is available
"$PYTHON" -c "import requests" 2>/dev/null || {
  echo "Installing requests ..."
  "$PYTHON" -m pip install --quiet requests
}

# Build env vars line for cron (cron has a minimal environment)
ENV_VARS=""
[[ -n "${GITHUB_TOKEN:-}" ]]  && ENV_VARS+="GITHUB_TOKEN=$GITHUB_TOKEN "
[[ -n "${GITHUB_USER:-}" ]]   && ENV_VARS+="GITHUB_USER=$GITHUB_USER "
[[ -n "${GITHUB_REPOS:-}" ]]  && ENV_VARS+="GITHUB_REPOS=\"$GITHUB_REPOS\" "
ENV_VARS+="COMMIT_LOG=$LOG_FILE"

CRON_CMD="0 */6 * * * $ENV_VARS $PYTHON $TRACKER >> $CRON_LOG 2>&1"

# Add to crontab (idempotent — remove old entry first)
( crontab -l 2>/dev/null | grep -v 'github_commit_tracker'; echo "$CRON_CMD" ) | crontab -

echo "Cron job installed. It will run at: 00:00, 06:00, 12:00, 18:00 UTC every day."
echo "Log file  : $LOG_FILE"
echo "Cron log  : $CRON_LOG"
echo ""
echo "Run a manual check right now with:"
echo "  $ENV_VARS $PYTHON $TRACKER"
