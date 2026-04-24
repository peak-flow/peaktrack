#!/usr/bin/env bash
# Checks peak-flow/peaktrack for commits in the last 6 hours and appends to commit-log.md.
# Requires GITHUB_TOKEN env var with repo read access.

set -euo pipefail

OWNER="peak-flow"
REPO="peaktrack"
LOG_FILE="$(dirname "$0")/../commit-log.md"
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SINCE=$(date -u -d "6 hours ago" +"%Y-%m-%dT%H:%M:%SZ")

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set." >&2
  exit 1
fi

API="https://api.github.com/repos/${OWNER}/${REPO}"
AUTH_HEADER="Authorization: Bearer ${GITHUB_TOKEN}"

# Fetch all branch names
branches=$(curl -sf -H "$AUTH_HEADER" \
  "${API}/branches?per_page=100" | \
  python3 -c "import sys,json; [print(b['name']) for b in json.load(sys.stdin)]")

declare -A branch_commits
total=0

for branch in $branches; do
  encoded_branch=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$branch")
  commits_json=$(curl -sf -H "$AUTH_HEADER" \
    "${API}/commits?sha=${encoded_branch}&since=${SINCE}&per_page=100" || echo "[]")

  count=$(echo "$commits_json" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)

  if [[ "$count" -gt 0 ]]; then
    branch_commits["$branch"]=$commits_json
    total=$((total + count))
  fi
done

# Build markdown entry
{
  echo ""
  echo "## ${NOW} — Window: $(echo "$SINCE" | grep -oP '\d{2}:\d{2}') → $(echo "$NOW" | grep -oP '\d{2}:\d{2}') UTC"
  echo ""

  if [[ "$total" -eq 0 ]]; then
    echo "**No commits in this window.**"
  else
    echo "| Branch | Commits | Authors |"
    echo "|--------|---------|---------|"
    for branch in "${!branch_commits[@]}"; do
      count=$(echo "${branch_commits[$branch]}" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
      authors=$(echo "${branch_commits[$branch]}" | python3 -c "
import sys, json
commits = json.load(sys.stdin)
names = list(dict.fromkeys(c['commit']['author']['name'] for c in commits))
print(', '.join(names))
")
      echo "| \`${branch}\` | ${count} | ${authors} |"
    done
    echo ""
    echo "**Total commits: ${total}**"
    echo ""
    echo "### Details"
    echo ""
    for branch in "${!branch_commits[@]}"; do
      count=$(echo "${branch_commits[$branch]}" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
      echo "- \`${branch}\` — ${count} commit(s)"
      echo "${branch_commits[$branch]}" | python3 -c "
import sys, json
for c in json.load(sys.stdin):
    sha = c['sha'][:7]
    msg = c['commit']['message'].splitlines()[0]
    author = c['commit']['author']['name']
    date = c['commit']['author']['date']
    print(f'  - \`{sha}\` {msg} *({author}, {date})*')
"
    done
  fi
  echo ""
  echo "---"
} >> "$LOG_FILE"

echo "Done. Total commits found: ${total}"
