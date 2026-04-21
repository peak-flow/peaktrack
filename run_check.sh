#!/usr/bin/env bash
# Wrapper called by cron — loads .env then runs check_commits.py
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SCRIPT_DIR/.env" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "$SCRIPT_DIR/.env"
    set +a
fi

python3 "$SCRIPT_DIR/check_commits.py"
