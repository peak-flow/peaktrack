#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$REPO_DIR/commit-log.md"
NOW="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
SINCE="$(date -u -d '6 hours ago' +"%Y-%m-%dT%H:%M:%SZ")"
SINCE_HUMAN="$(date -u -d '6 hours ago' +"%Y-%m-%d %H:%M UTC")"
NOW_HUMAN="$(date -u +"%Y-%m-%d %H:%M UTC")"

# Initialise log file if missing
if [ ! -f "$LOG_FILE" ]; then
  printf '# GitHub Commit Log — peak-flow/peaktrack\n\nAuto-generated every 6 hours.\n\n' > "$LOG_FILE"
fi

# Fetch latest from all remotes
cd "$REPO_DIR"
git fetch --all --quiet 2>/dev/null || true

# Collect commits across all remote tracking branches since 6h ago
COMMITS=$(git log --remotes --since="$SINCE" \
  --pretty=format:'- **%h** %s _(author: %an, branch: %D, at %ai)_' \
  --date=iso 2>/dev/null || true)

COUNT=0
if [ -n "$COMMITS" ]; then
  COUNT=$(echo "$COMMITS" | wc -l)
fi

# Build the markdown entry
{
  printf '\n---\n\n'
  printf '## %s\n\n' "$NOW_HUMAN"
  printf '**Period checked:** %s → %s\n\n' "$SINCE_HUMAN" "$NOW_HUMAN"
  printf '**Total commits:** %d\n\n' "$COUNT"
  if [ "$COUNT" -gt 0 ]; then
    printf '### Commits\n\n'
    echo "$COMMITS"
    printf '\n'
  else
    printf '_No commits in this window._\n'
  fi
} >> "$LOG_FILE"

echo "DONE|$NOW|commits=$COUNT"
