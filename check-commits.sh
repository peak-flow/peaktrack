#!/usr/bin/env bash
# Fetches commits from peak-flow/peaktrack made in the last 6 hours
# and appends a summary to commit-activity.md.
# Requires: GITHUB_TOKEN env var set to a Personal Access Token

set -euo pipefail

OWNER="peak-flow"
REPO="peaktrack"
LOG_FILE="$(dirname "$0")/commit-activity.md"

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set. Export your GitHub PAT before running." >&2
  exit 1
fi

NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SINCE=$(date -u -d '6 hours ago' +%Y-%m-%dT%H:%M:%SZ)

RESPONSE=$(curl -s \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${OWNER}/${REPO}/commits?since=${SINCE}&per_page=100")

COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data) if isinstance(data,list) else 0)")

{
  echo "## Check: ${NOW}"
  echo "- **Commits in last 6 hours:** ${COUNT}"
  echo "- **Repository:** ${OWNER}/${REPO}"
  echo "- **Details:**"

  if [[ "$COUNT" -eq 0 ]]; then
    echo "  - No commits in the last 6 hours."
  else
    echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data:
    sha = c['sha'][:7]
    author = (c.get('commit',{}).get('author') or {}).get('name','unknown')
    msg = (c.get('commit',{}).get('message') or '').split('\n')[0]
    ts = (c.get('commit',{}).get('author') or {}).get('date','')
    print(f'  - \`{sha}\` — {author} — {msg} ({ts})')
"
  fi

  echo ""
} >> "$LOG_FILE"

echo "Logged ${COUNT} commit(s) at ${NOW}"
