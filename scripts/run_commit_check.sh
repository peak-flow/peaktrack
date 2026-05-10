#!/usr/bin/env bash
# Wrapper executed by cron every 6 hours.
# Edit the variables below to match your setup before installing the cron job.

set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

export GITHUB_TOKEN="${GITHUB_TOKEN:-}"          # or hard-code here (keep file private)
export GITHUB_REPOS="${GITHUB_REPOS:-}"          # e.g. "peak-flow/peaktrack,peak-flow/other"
export GITHUB_ORG="${GITHUB_ORG:-peak-flow}"     # used when GITHUB_REPOS is empty
export REPORT_DIR="${REPORT_DIR:-$REPO_ROOT/commit_reports}"
export HOURS="${HOURS:-6}"
# ───────────────────────────────────────────────────────────────────────────────

if [[ -z "$GITHUB_TOKEN" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set. Export it before running this script." >&2
  exit 1
fi

python3 "$SCRIPT_DIR/check_commits.py"
