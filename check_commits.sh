#!/usr/bin/env bash
# Checks GitHub for commits in the last 6 hours and appends a summary to commit_log.md

set -euo pipefail

GITHUB_TOKEN="${GITHUB_TOKEN:-}"
LOG_FILE="$(dirname "$0")/commit_log.md"
REPOS=("peak-flow/peaktrack")

if [[ -z "$GITHUB_TOKEN" ]]; then
  echo "Error: GITHUB_TOKEN environment variable is not set." >&2
  exit 1
fi

NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SINCE=$(date -u -d "6 hours ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
        || date -u -v-6H +"%Y-%m-%dT%H:%M:%SZ")  # macOS fallback

{
  echo ""
  echo "## $NOW"
  echo ""
  echo "| Repo | Commits (last 6h) |"
  echo "|------|-------------------|"
} >> "$LOG_FILE"

TOTAL=0

for REPO in "${REPOS[@]}"; do
  OWNER="${REPO%%/*}"
  REPONAME="${REPO##*/}"

  RESPONSE=$(curl -sSL \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/$OWNER/$REPONAME/commits?since=$SINCE&per_page=100")

  COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data))" 2>/dev/null || echo "0")

  echo "| $REPO | $COUNT |" >> "$LOG_FILE"
  TOTAL=$((TOTAL + COUNT))

  if [[ "$COUNT" -gt 0 ]]; then
    {
      echo ""
      echo "### $REPO — $COUNT commit(s)"
      echo ""
      echo "$RESPONSE" | python3 -c "
import sys, json
commits = json.load(sys.stdin)
for c in commits:
    sha = c['sha'][:7]
    msg = c['commit']['message'].split('\n')[0]
    author = c['commit']['author']['name']
    date = c['commit']['author']['date']
    print(f'- \`{sha}\` {date} **{author}**: {msg}')
"
    } >> "$LOG_FILE"
  fi
done

if [[ "$TOTAL" -eq 0 ]]; then
  echo "" >> "$LOG_FILE"
  echo "No commits found in the last 6 hours." >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"

echo "Done. Total commits in last 6h: $TOTAL"
