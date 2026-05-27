#!/usr/bin/env bash
# Fetches commits from the last 6 hours across repos and appends a summary to reports/commit_log.md
set -euo pipefail

REPORT_FILE="$(dirname "$0")/../reports/commit_log.md"
SINCE=$(date -u -d '6 hours ago' '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u -v-6H '+%Y-%m-%dT%H:%M:%SZ')
NOW=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
TOKEN="${GITHUB_TOKEN:-}"

if [[ -z "$TOKEN" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set. Export it before running this script." >&2
  exit 1
fi

AUTH_HEADER="Authorization: Bearer $TOKEN"

# Fetch all repos the authenticated user has push access to (up to 100)
repos=$(curl -sf -H "$AUTH_HEADER" \
  "https://api.github.com/user/repos?per_page=100&sort=pushed&type=all" \
  | jq -r '.[].full_name')

if [[ -z "$repos" ]]; then
  echo "No repos found or API call failed." >&2
  exit 1
fi

total_commits=0
declare -A repo_counts

for repo in $repos; do
  count=$(curl -sf -H "$AUTH_HEADER" \
    "https://api.github.com/repos/$repo/commits?since=$SINCE&per_page=100" \
    | jq 'length' 2>/dev/null || echo 0)
  if [[ "$count" -gt 0 ]]; then
    repo_counts["$repo"]=$count
    total_commits=$((total_commits + count))
  fi
done

# Build markdown section
{
  echo ""
  echo "## Commit Report: $NOW"
  echo ""
  echo "**Period:** last 6 hours (since $SINCE)"
  echo ""
  echo "**Total commits:** $total_commits"
  echo ""
  if [[ ${#repo_counts[@]} -eq 0 ]]; then
    echo "_No commits found in any repository._"
  else
    echo "| Repository | Commits |"
    echo "|---|---|"
    for repo in "${!repo_counts[@]}"; do
      echo "| \`$repo\` | ${repo_counts[$repo]} |"
    done
  fi
  echo ""
  echo "---"
} >> "$REPORT_FILE"

echo "Done. $total_commits commit(s) found across ${#repo_counts[@]} repo(s). Appended to $REPORT_FILE"
