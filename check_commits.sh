#!/usr/bin/env bash
# Checks commits on peak-flow/peaktrack for the last 6 hours and appends to commit_log.md
set -euo pipefail

LOG=/home/user/peaktrack/commit_log.md
OWNER=peak-flow
REPO=peaktrack
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SINCE=$(date -u -d '6 hours ago' +%Y-%m-%dT%H:%M:%SZ)

# Fetch commits via GitHub API (requires GITHUB_TOKEN env var)
RESPONSE=$(curl -sf \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${OWNER}/${REPO}/commits?since=${SINCE}&until=${NOW}&per_page=100" \
  2>/dev/null || echo "[]")

COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data))" 2>/dev/null || echo 0)

{
  echo "## ${NOW}"
  echo ""
  echo "**Repository:** \`${OWNER}/${REPO}\`"
  echo "**Window:** ${SINCE} → ${NOW}"
  echo "**Total commits:** ${COUNT}"
  echo ""
  if [ "$COUNT" -eq 0 ]; then
    echo "_No commits in this window._"
  else
    echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data:
    sha = c['sha'][:7]
    author = c['commit']['author']['name']
    msg = c['commit']['message'].split('\n')[0]
    print(f'- \`{sha}\` **{author}**: {msg}')
"
  fi
  echo ""
  echo "---"
  echo ""
} >> "$LOG"

echo "DONE: ${COUNT} commits recorded at ${NOW}"
