#!/usr/bin/env bash
# Checks GitHub commits in the last 6 hours and appends to commit-activity-log.md
# Requires: GITHUB_TOKEN env var set with repo read access

set -euo pipefail

LOG_FILE="/home/user/peaktrack/commit-activity-log.md"
REPOS=("peak-flow/peaktrack")
NOW_UTC=$(date -u +"%Y-%m-%d %H:%M")
SINCE=$(date -u -d "6 hours ago" +"%Y-%m-%dT%H:%M:%SZ")

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set. Export it before running this script." >&2
  exit 1
fi

# Append section header
{
  echo ""
  echo "## ${NOW_UTC} UTC"
  echo ""
  echo "| Repository | Commits (last 6h) | Top Committers |"
  echo "|---|---|---|"
} >> "$LOG_FILE"

for REPO in "${REPOS[@]}"; do
  OWNER="${REPO%%/*}"
  NAME="${REPO##*/}"

  RESPONSE=$(curl -s \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${OWNER}/${NAME}/commits?since=${SINCE}&per_page=100")

  COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data))" 2>/dev/null || echo 0)

  if [[ "$COUNT" -gt 0 ]]; then
    TOP=$(echo "$RESPONSE" | python3 -c "
import sys, json
from collections import Counter
data = json.load(sys.stdin)
authors = [c['commit']['author']['name'] for c in data]
counts = Counter(authors).most_common(3)
print(', '.join(f'{n} ({c})' for n,c in counts))
" 2>/dev/null || echo "unknown")
  else
    TOP="—"
  fi

  echo "| ${REPO} | ${COUNT} | ${TOP} |" >> "$LOG_FILE"
done

echo "" >> "$LOG_FILE"

# Print commit details if any
for REPO in "${REPOS[@]}"; do
  OWNER="${REPO%%/*}"
  NAME="${REPO##*/}"

  RESPONSE=$(curl -s \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${OWNER}/${NAME}/commits?since=${SINCE}&per_page=100")

  COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data))" 2>/dev/null || echo 0)

  if [[ "$COUNT" -gt 0 ]]; then
    {
      echo "### ${REPO} — ${COUNT} commit(s)"
      echo ""
      echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data:
    sha = c['sha'][:7]
    msg = c['commit']['message'].splitlines()[0]
    author = c['commit']['author']['name']
    date = c['commit']['author']['date'][:16].replace('T',' ')
    print(f'- \`{sha}\` {date} UTC — **{author}**: {msg}')
"
      echo ""
    } >> "$LOG_FILE"
  fi
done

echo "---" >> "$LOG_FILE"
echo "Log updated: ${NOW_UTC} UTC"
