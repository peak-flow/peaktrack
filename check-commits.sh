#!/usr/bin/env bash
set -euo pipefail

# Requires GITHUB_TOKEN env var — set it in /etc/environment or ~/.profile
if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set. Export it before running this script." >&2
  exit 1
fi

OWNER="peak-flow"
REPO="peaktrack"
LOG_FILE="$(dirname "$(realpath "$0")")/commit-log.md"
SINCE=$(date -u -d '6 hours ago' +%Y-%m-%dT%H:%M:%SZ)
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)

RESPONSE=$(curl -sf \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$OWNER/$REPO/commits?since=$SINCE&per_page=100")

COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)

{
  echo ""
  echo "## $NOW"
  echo ""
  echo "**Repo:** \`$OWNER/$REPO\`  "
  echo "**Period:** $SINCE → $NOW  "
  echo "**Commits in last 6 hours:** $COUNT"
  echo ""

  if [[ "$COUNT" -gt 0 ]]; then
    echo "| SHA | Author | Message |"
    echo "|-----|--------|---------|"
    echo "$RESPONSE" | python3 -c "
import sys, json
for c in json.load(sys.stdin):
    sha = c['sha'][:7]
    author = (c.get('commit',{}).get('author',{}).get('name','') or
              (c.get('author') or {}).get('login','unknown'))
    msg = c['commit']['message'].splitlines()[0][:80]
    print(f'| \`{sha}\` | {author} | {msg} |')
"
  else
    echo "_No commits found in this period._"
  fi

  echo ""
  echo "---"
} >> "$LOG_FILE"

echo "[$(date -u +%H:%M:%SZ)] Logged $COUNT commit(s) to $LOG_FILE"
