#!/usr/bin/env bash
# Wrapper called by cron. Loads GITHUB_TOKEN from ~/.github_token if present.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load token from file if env var is not already set
if [[ -z "${GITHUB_TOKEN:-}" ]] && [[ -f "$HOME/.github_token" ]]; then
    export GITHUB_TOKEN="$(cat "$HOME/.github_token")"
fi

python3 "$SCRIPT_DIR/check_commits.py" \
    --hours 6 \
    --output "$PROJECT_ROOT/commit_log.md"
