#!/usr/bin/env bash
# Queries GitHub API for commits in the last 6 hours and appends a summary
# to commit-activity.md. Requires GITHUB_TOKEN to be set.

set -euo pipefail

REPO_OWNER="peak-flow"
REPO_NAME="peaktrack"
LOG_FILE="$(dirname "$0")/../commit-activity.md"
HOURS=6

if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "ERROR: GITHUB_TOKEN is not set" >&2
  exit 1
fi

SINCE=$(date -u -d "${HOURS} hours ago" +%Y-%m-%dT%H:%M:%SZ)
NOW=$(date -u +"%Y-%m-%d %H:%M UTC")

response=$(curl -s -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/commits?since=${SINCE}&per_page=100")

commit_count=$(echo "$response" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data))" 2>/dev/null || echo 0)

commit_list=""
if [ "$commit_count" -gt 0 ]; then
  commit_list=$(echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data:
    sha = c['sha'][:7]
    msg = c['commit']['message'].splitlines()[0][:80]
    author = c['commit']['author']['name']
    print(f'- \`{sha}\` {msg} — *{author}*')
" 2>/dev/null || echo "- (could not parse commits)")
fi

{
  echo ""
  echo "## ${NOW}"
  echo ""
  echo "| Repo | Commits |"
  echo "|------|---------|"
  echo "| ${REPO_OWNER}/${REPO_NAME} | ${commit_count} |"
  echo ""
  if [ "$commit_count" -gt 0 ]; then
    echo "**Commits:**"
    echo ""
    echo "$commit_list"
  else
    echo "**No commits in the last ${HOURS} hours.**"
  fi
  echo ""
  echo "---"
} >> "$LOG_FILE"

echo "Logged ${commit_count} commit(s) at ${NOW}"
