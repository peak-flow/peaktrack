#!/usr/bin/env bash
# Checks commits made in the last 6 hours and appends a summary to commit_log.md.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$REPO_DIR/commit_log.md"
REPO_LABEL="peak-flow/peaktrack"
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SINCE=$(date -u -d "6 hours ago" +"%Y-%m-%dT%H:%M:%SZ")
SINCE_HUMAN=$(date -u -d "6 hours ago" +"%Y-%m-%d %H:%M:%S UTC")
NOW_HUMAN=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

cd "$REPO_DIR"

# Fetch latest from remote silently
git fetch origin --quiet 2>/dev/null || true

# Collect commits from the last 6 hours on all remote branches
COMMITS=$(git log --remotes --no-merges \
  --since="6 hours ago" \
  --format="%H|%s|%an|%ai" 2>/dev/null || true)

COUNT=$(echo "$COMMITS" | grep -c '|' || echo 0)
if [ -z "$COMMITS" ]; then COUNT=0; fi

# Build markdown entry
{
  echo "## $NOW_HUMAN"
  echo ""
  echo "| Field | Value |"
  echo "|-------|-------|"
  echo "| **Repository** | $REPO_LABEL |"
  echo "| **Window** | $SINCE → $NOW |"
  echo "| **Commit count** | $COUNT |"
  echo ""

  if [ "$COUNT" -eq 0 ]; then
    echo "_No commits in this window._"
  else
    echo "| SHA | Message | Author |"
    echo "|-----|---------|--------|"
    while IFS='|' read -r sha msg author date; do
      short_sha="${sha:0:7}"
      echo "| \`$short_sha\` | $msg | $author |"
    done <<< "$COMMITS"
  fi

  echo ""
  echo "---"
  echo ""
} >> "$LOG_FILE"

echo "[$NOW] Logged $COUNT commit(s) to $LOG_FILE"
