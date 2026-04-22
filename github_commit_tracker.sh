#!/usr/bin/env bash
# Fetches commits made in the last 6 hours across GitHub repos and appends a summary to a markdown file.
# Requires: curl, jq
# Env vars: GITHUB_TOKEN (required), GITHUB_USERNAME (required), COMMIT_LOG_FILE (optional, default: commit_log.md)

set -euo pipefail

GITHUB_TOKEN="${GITHUB_TOKEN:?GITHUB_TOKEN env var is required}"
GITHUB_USERNAME="${GITHUB_USERNAME:?GITHUB_USERNAME env var is required}"
OUTPUT_FILE="${COMMIT_LOG_FILE:-/home/user/peaktrack/commit_log.md}"
API="https://api.github.com"
HOURS=6

# ISO 8601 timestamp for N hours ago (portable: works without GNU date)
since=$(date -u -d "${HOURS} hours ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
  || python3 -c "from datetime import datetime, timedelta, timezone; print((datetime.now(timezone.utc) - timedelta(hours=${HOURS})).strftime('%Y-%m-%dT%H:%M:%SZ'))")

now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "Checking commits since ${since} ..."

auth_header="Authorization: Bearer ${GITHUB_TOKEN}"

# Fetch all repos (up to 100 per page; extend pagination if needed)
repos=$(curl -sf \
  -H "$auth_header" \
  -H "Accept: application/vnd.github+json" \
  "${API}/users/${GITHUB_USERNAME}/repos?per_page=100&type=all" \
  | jq -r '.[].full_name')

declare -A repo_counts
total_commits=0

for repo in $repos; do
  count=$(curl -sf \
    -H "$auth_header" \
    -H "Accept: application/vnd.github+json" \
    "${API}/repos/${repo}/commits?since=${since}&per_page=100" \
    | jq 'length')

  if [[ "$count" -gt 0 ]]; then
    repo_counts["$repo"]=$count
    total_commits=$((total_commits + count))
  fi
done

# Append report to markdown file
{
  echo ""
  echo "## Commit Report — ${now}"
  echo ""
  echo "**Window:** last ${HOURS} hours (since \`${since}\`)"
  echo ""
  echo "**Total commits:** ${total_commits}"
  echo ""

  if [[ ${#repo_counts[@]} -eq 0 ]]; then
    echo "_No commits found in this window._"
  else
    echo "| Repository | Commits |"
    echo "|------------|---------|"
    for repo in "${!repo_counts[@]}"; do
      echo "| \`${repo}\` | ${repo_counts[$repo]} |"
    done
  fi

  echo ""
  echo "---"
} >> "$OUTPUT_FILE"

echo "Report appended to ${OUTPUT_FILE} (total commits: ${total_commits})"
