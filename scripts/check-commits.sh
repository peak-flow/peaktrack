#!/usr/bin/env bash
# Wrapper for cron: sources user env then runs check-commits.py
# Set GITHUB_TOKEN in /home/user/.profile or /home/user/.env-tokens

set -euo pipefail

# Source user profile to pick up GITHUB_TOKEN if set there
if [[ -f /home/user/.profile ]]; then
    # shellcheck source=/dev/null
    source /home/user/.profile 2>/dev/null || true
fi

# Also check a dedicated secrets file if present
if [[ -f /home/user/.env-tokens ]]; then
    # shellcheck source=/dev/null
    source /home/user/.env-tokens 2>/dev/null || true
fi

exec python3 /home/user/peaktrack/scripts/check-commits.py "$@"
