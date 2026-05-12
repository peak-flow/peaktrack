#!/usr/bin/env bash
# Checks GitHub for commits in the last 6 hours and appends a report to commit_log.md

set -euo pipefail

GITHUB_TOKEN="${GITHUB_TOKEN:-}"
HOURS=6
OUTPUT_FILE="$(dirname "$0")/commit_log.md"
API="https://api.github.com"

if [[ -z "$GITHUB_TOKEN" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set. Export it before running this script." >&2
  exit 1
fi

SINCE=$(date -u -d "-${HOURS} hours" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
     || date -u -v-"${HOURS}"H +"%Y-%m-%dT%H:%M:%SZ")  # macOS fallback

NOW=$(date -u +"%Y-%m-%d %H:%M UTC")

auth_curl() {
  curl -fsSL \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "$@"
}

# Fetch all repos the token has access to (up to 100 per page, page through)
fetch_repos() {
  local page=1
  while true; do
    local result
    result=$(auth_curl "${API}/user/repos?per_page=100&page=${page}&sort=pushed&direction=desc")
    local count
    count=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d))" 2>/dev/null || echo 0)
    echo "$result" | python3 -c "import sys,json; [print(r['full_name']) for r in json.load(sys.stdin)]" 2>/dev/null || true
    [[ "$count" -lt 100 ]] && break
    ((page++))
  done
}

# Count commits to a repo since $SINCE
count_commits() {
  local repo="$1"
  local result
  result=$(auth_curl "${API}/repos/${repo}/commits?since=${SINCE}&per_page=100" 2>/dev/null) || return 0
  echo "$result" | python3 -c "import sys,json
try:
  d=json.load(sys.stdin)
  print(len(d) if isinstance(d,list) else 0)
except:
  print(0)
" 2>/dev/null || echo 0
}

# Build the report
{
  echo "## Commit Report — $NOW (last ${HOURS}h)"
  echo ""
  echo "| Repository | Commits |"
  echo "|---|---|"
} > /tmp/commit_report_tmp.md

total=0
active_repos=0

while IFS= read -r repo; do
  count=$(count_commits "$repo")
  if [[ "$count" -gt 0 ]]; then
    echo "| \`${repo}\` | ${count} |" >> /tmp/commit_report_tmp.md
    total=$((total + count))
    active_repos=$((active_repos + 1))
  fi
done < <(fetch_repos)

{
  echo ""
  echo "**Total: ${total} commit(s) across ${active_repos} repo(s)**"
  echo ""
  echo "---"
  echo ""
} >> /tmp/commit_report_tmp.md

# Prepend new report to the log file (newest first)
if [[ -f "$OUTPUT_FILE" ]]; then
  cat /tmp/commit_report_tmp.md "$OUTPUT_FILE" > /tmp/commit_log_merged.md
  mv /tmp/commit_log_merged.md "$OUTPUT_FILE"
else
  echo "# GitHub Commit Log" > "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"
  cat /tmp/commit_report_tmp.md >> "$OUTPUT_FILE"
fi

rm -f /tmp/commit_report_tmp.md
echo "Report written to $OUTPUT_FILE (${total} commits across ${active_repos} repos)"
