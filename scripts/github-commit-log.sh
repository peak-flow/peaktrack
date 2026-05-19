#!/usr/bin/env bash
# Checks all repos in a GitHub org for commits in the last 6 hours and appends
# a markdown summary to commit-log.md.
#
# Requirements:
#   - GITHUB_TOKEN env var with repo read access
#   - curl, jq
#
# Cron (every 6 hours):
#   0 */6 * * * GITHUB_TOKEN=ghp_xxx /path/to/github-commit-log.sh

set -euo pipefail

ORG="peak-flow"
LOG_FILE="$(dirname "$0")/../commit-log.md"
API="https://api.github.com"
HOURS=6

now=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
since=$(date -u -d "${HOURS} hours ago" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null \
       || date -u -v-${HOURS}H '+%Y-%m-%dT%H:%M:%SZ')  # macOS fallback

window_start=$since
window_end=$now

auth_header="Authorization: Bearer ${GITHUB_TOKEN}"

echo "Checking ${ORG} repos for commits since ${since}..."

# Fetch all repos (paginate)
repos=()
page=1
while true; do
  result=$(curl -sf -H "$auth_header" \
    "${API}/orgs/${ORG}/repos?per_page=100&page=${page}&sort=pushed&direction=desc" \
    | jq -r '.[].name')
  [[ -z "$result" ]] && break
  while IFS= read -r repo; do
    repos+=("$repo")
  done <<< "$result"
  count=$(echo "$result" | wc -l)
  (( count < 100 )) && break
  (( page++ ))
done

echo "Found ${#repos[@]} repos."

declare -A commit_counts
total=0

for repo in "${repos[@]}"; do
  count=$(curl -sf -H "$auth_header" \
    "${API}/repos/${ORG}/${repo}/commits?since=${since}&per_page=100" \
    | jq 'length' 2>/dev/null || echo 0)
  if (( count > 0 )); then
    commit_counts["$repo"]=$count
    (( total += count ))
  fi
done

# Build markdown table rows (only repos with commits)
if (( ${#commit_counts[@]} == 0 )); then
  table_rows="| *(no repos had commits this window)* | 0 |"
else
  table_rows=""
  for repo in "${!commit_counts[@]}"; do
    table_rows+="| ${ORG}/${repo} | ${commit_counts[$repo]} |"$'\n'
  done
fi

# Append to log file
cat >> "$LOG_FILE" <<EOF

## ${window_end} (window: ${window_start} → ${window_end})

| Repository | Commits |
|---|---|
${table_rows}
**Total commits this window: ${total}**

---
EOF

echo "Done. Appended to ${LOG_FILE}"
