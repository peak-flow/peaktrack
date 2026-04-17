#!/usr/bin/env bash
# Checks peak-flow/peaktrack for commits in the last 6 hours and appends to commit_log.md.
# Requires GITHUB_TOKEN env var or a token stored in ~/.github_token.

set -euo pipefail

OWNER="peak-flow"
REPO="peaktrack"
LOG="/home/user/peaktrack/commit_log.md"
HOURS=6

# Load token
if [ -z "${GITHUB_TOKEN:-}" ]; then
  if [ -f "$HOME/.github_token" ]; then
    GITHUB_TOKEN=$(cat "$HOME/.github_token")
  else
    echo "ERROR: No GITHUB_TOKEN set and ~/.github_token not found." >&2
    exit 1
  fi
fi

SINCE=$(date -u -d "${HOURS} hours ago" '+%Y-%m-%dT%H:%M:%SZ')
NOW=$(date -u '+%Y-%m-%d %H:%M:%S UTC')
WINDOW_START=$(date -u -d "${HOURS} hours ago" '+%Y-%m-%d %H:%M UTC')
WINDOW_END=$(date -u '+%Y-%m-%d %H:%M UTC')

api() {
  curl -fsSL \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "$@"
}

# Get all branches
branches=$(api "https://api.github.com/repos/${OWNER}/${REPO}/branches?per_page=100" \
  | python3 -c "import sys,json; [print(b['name']) for b in json.load(sys.stdin)]")

total=0
table_rows=""
commit_details=""

while IFS= read -r branch; do
  # Fetch commits on this branch since SINCE
  encoded_branch=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$branch")
  commits_json=$(api "https://api.github.com/repos/${OWNER}/${REPO}/commits?sha=${encoded_branch}&since=${SINCE}&per_page=100" 2>/dev/null || echo "[]")

  count=$(echo "$commits_json" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data))" 2>/dev/null || echo 0)
  total=$((total + count))
  table_rows="${table_rows}| \`${branch}\` | ${count} |"$'\n'

  if [ "$count" -gt 0 ]; then
    msgs=$(echo "$commits_json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data:
    sha = c['sha'][:7]
    msg = c['commit']['message'].split('\n')[0]
    author = c['commit']['author']['name']
    date = c['commit']['author']['date'][:10]
    print(f'  - \`{sha}\` {date} **{author}**: {msg}')
")
    commit_details="${commit_details}"$'\n'"**Branch \`${branch}\`:**"$'\n'"${msgs}"$'\n'
  fi
done <<< "$branches"

# Build markdown entry
entry="## ${NOW}

**Repo:** ${OWNER}/${REPO}
**Window:** ${WINDOW_START} → ${WINDOW_END}
**Total commits:** ${total}

| Branch | Commits |
|--------|---------|
${table_rows}"

if [ "$total" -gt 0 ]; then
  entry="${entry}
### Commit details
${commit_details}"
else
  entry="${entry}
_No new commits in this window._"
fi

entry="${entry}

---
"

printf '\n%s\n' "$entry" >> "$LOG"
echo "Done. ${total} commits logged to ${LOG}"
