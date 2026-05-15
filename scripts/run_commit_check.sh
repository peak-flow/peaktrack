#!/usr/bin/env bash
# Wrapper for check_commits.py — suitable for cron.
# Add to crontab with: crontab -e
#   0 */6 * * * /home/user/peaktrack/scripts/run_commit_check.sh >> /home/user/peaktrack/scripts/cron.log 2>&1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load token from .env if not already set
if [[ -z "${GITHUB_TOKEN:-}" && -f "$SCRIPT_DIR/../.env" ]]; then
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/../.env"
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
    echo "ERROR: GITHUB_TOKEN is not set" >&2
    exit 1
fi

# Comma-separated list of repos to check (override via env or edit here)
export GITHUB_REPOS="${GITHUB_REPOS:-peak-flow/peaktrack}"
export GITHUB_TOKEN

python3 "$SCRIPT_DIR/check_commits.py"
