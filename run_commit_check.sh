#!/usr/bin/env bash
# Wrapper for cron — loads token from ~/.github_token if not already set.
# Cron line: 0 */6 * * * /home/user/peaktrack/run_commit_check.sh

set -euo pipefail

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
    TOKEN_FILE="$HOME/.github_token"
    if [[ -f "$TOKEN_FILE" ]]; then
        export GITHUB_TOKEN="$(cat "$TOKEN_FILE")"
    else
        echo "$(date -u): ERROR — GITHUB_TOKEN not set and $TOKEN_FILE not found" \
            >> /home/user/peaktrack/check_commits.log
        exit 1
    fi
fi

exec /usr/local/bin/python3 /home/user/peaktrack/check_commits.py \
    >> /home/user/peaktrack/check_commits.log 2>&1
