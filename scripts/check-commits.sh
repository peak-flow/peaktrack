#!/usr/bin/env bash
# Checks peak-flow/peaktrack for commits in the last 6 hours and appends to commit-log.md.
# Requires: gh CLI authenticated, or GITHUB_TOKEN set in environment.

set -euo pipefail

OWNER="peak-flow"
REPO="peaktrack"
LOG_FILE="$(dirname "$0")/../commit-log.md"
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SINCE=$(date -u -d "6 hours ago" +"%Y-%m-%dT%H:%M:%SZ")
DISPLAY_NOW=$(date -u +"%Y-%m-%d %H:%M UTC")

# Fetch commits since 6 hours ago (GitHub API, up to 100)
RESPONSE=$(curl -s \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${OWNER}/${REPO}/commits?since=${SINCE}&until=${NOW}&per_page=100")

COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data))")

{
  echo "## ${DISPLAY_NOW}"
  echo ""
  echo "**Repository:** \`${OWNER}/${REPO}\`"
  echo "**Window:** ${SINCE} → ${NOW}"
  echo "**Commits in window:** ${COUNT}"
  echo ""

  if [ "$COUNT" -eq 0 ]; then
    echo "_No commits in this period._"
  else
    echo "| SHA | Author | Message |"
    echo "|-----|--------|---------|"
    echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data:
    sha = c['sha'][:7]
    author = c['commit']['author']['name']
    msg = c['commit']['message'].splitlines()[0][:80]
    print(f'| \`{sha}\` | {author} | {msg} |')
"
  fi

  echo ""
  echo "---"
  echo ""
} >> "$LOG_FILE"

echo "[${DISPLAY_NOW}] Logged ${COUNT} commits to ${LOG_FILE}"
