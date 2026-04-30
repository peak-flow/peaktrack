#!/usr/bin/env bash
set -euo pipefail

# Requires GITHUB_TOKEN environment variable to be set.
# Checks all accessible repos for commits in the last 6 hours and appends a
# summary to commit-log.md.

LOG_FILE="$(dirname "$(realpath "$0")")/../commit-log.md"
API="https://api.github.com"
SINCE=$(date -u -d '6 hours ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
        || date -u -v-6H +%Y-%m-%dT%H:%M:%SZ)   # Linux / macOS compat
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set." >&2
  exit 1
fi

auth_header="Authorization: Bearer ${GITHUB_TOKEN}"

# Fetch all repos the token has access to (up to 100 per page; extend if needed)
repos=$(curl -s -H "$auth_header" \
  "${API}/user/repos?per_page=100&sort=updated&direction=desc" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
for r in data:
    print(r['full_name'])
")

total_commits=0
declare -A repo_counts

while IFS= read -r repo; do
  [[ -z "$repo" ]] && continue
  owner="${repo%%/*}"
  name="${repo##*/}"

  # Fetch commits since 6 hours ago for this repo
  result=$(curl -s -H "$auth_header" \
    "${API}/repos/${owner}/${name}/commits?since=${SINCE}&per_page=100")

  count=$(echo "$result" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if isinstance(data, list):
        print(len(data))
    else:
        print(0)
except:
    print(0)
")

  if [[ "$count" -gt 0 ]]; then
    repo_counts["$repo"]=$count
    total_commits=$((total_commits + count))
  fi
done <<< "$repos"

# Build markdown entry
{
  echo ""
  echo "## $(date -u '+%Y-%m-%d %H:%M UTC')"
  echo ""
  echo "**Window:** ${SINCE} → ${NOW}"
  echo ""
  echo "**Total commits:** ${total_commits}"
  echo ""
  if [[ ${#repo_counts[@]} -eq 0 ]]; then
    echo "_No commits found in any accessible repository._"
  else
    echo "| Repository | Commits |"
    echo "|---|---|"
    for repo in "${!repo_counts[@]}"; do
      echo "| \`${repo}\` | ${repo_counts[$repo]} |"
    done
  fi
  echo ""
  echo "---"
} >> "$LOG_FILE"

echo "Done. Total commits: ${total_commits} across ${#repo_counts[@]} repo(s). Appended to ${LOG_FILE}"
