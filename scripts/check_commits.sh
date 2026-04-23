#!/usr/bin/env bash
# Checks commits on peak-flow/peaktrack in the last 6 hours and appends to commit_log.md
# Requires: GITHUB_TOKEN env var or ~/.github_token file

set -euo pipefail

REPO_OWNER="peak-flow"
REPO_NAME="peaktrack"
LOG_FILE="/home/user/peaktrack/commit_log.md"
HOURS=6

# Load token
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
  TOKEN="$GITHUB_TOKEN"
elif [[ -f "$HOME/.github_token" ]]; then
  TOKEN="$(cat "$HOME/.github_token")"
else
  echo "ERROR: No GitHub token found. Set GITHUB_TOKEN or create ~/.github_token" >&2
  exit 1
fi

NOW_DISPLAY=$(date -u +"%Y-%m-%d %H:%M UTC")
SINCE=$(date -u -d "${HOURS} hours ago" +%Y-%m-%dT%H:%M:%SZ)

# Fetch all commits since SINCE (paginate)
PAGE=1
ALL_COMMITS="[]"
while true; do
  RESPONSE=$(curl -sf \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/commits?since=${SINCE}&per_page=100&page=${PAGE}")

  PAGE_COUNT=$(echo "$RESPONSE" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
  ALL_COMMITS=$(python3 -c "
import json, sys
a = json.loads(sys.argv[1])
b = json.loads(sys.argv[2])
print(json.dumps(a + b))
" "$ALL_COMMITS" "$RESPONSE")

  if [[ "$PAGE_COUNT" -lt 100 ]]; then
    break
  fi
  PAGE=$((PAGE + 1))
done

TOTAL=$(echo "$ALL_COMMITS" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")

# Build markdown entry
{
  echo ""
  echo "## ${NOW_DISPLAY}"
  echo ""
  echo "**Repository:** ${REPO_OWNER}/${REPO_NAME}  "
  echo "**Window:** last ${HOURS} hours (since ${SINCE})  "
  echo "**Commits:** ${TOTAL}"
  echo ""
  if [[ "$TOTAL" -eq 0 ]]; then
    echo "_No commits in this period._"
  else
    echo "$ALL_COMMITS" | python3 -c "
import json, sys
commits = json.load(sys.stdin)
for c in commits:
    sha = c['sha'][:7]
    author = (c.get('commit', {}).get('author') or {}).get('name', 'unknown')
    msg = (c.get('commit', {}).get('message') or '').split('\n')[0][:80]
    print(f'- \`{sha}\` **{author}**: {msg}')
"
  fi
  echo ""
  echo "---"
} >> "$LOG_FILE"

echo "Logged ${TOTAL} commit(s) from ${REPO_OWNER}/${REPO_NAME} to ${LOG_FILE}"
