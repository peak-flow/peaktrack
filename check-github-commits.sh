#!/usr/bin/env bash
# Queries GitHub for commits in the last 6 hours across all peak-flow repos.
# Appends a summary entry to github-commit-log.md.
#
# Requirements: curl, jq
# Setup: export GITHUB_TOKEN=ghp_yourtoken
#
# Cron example (every 6 hours):
#   0 */6 * * * GITHUB_TOKEN=ghp_yourtoken /path/to/check-github-commits.sh

set -euo pipefail

GITHUB_USER="${GITHUB_USER:-peak-flow}"
LOG_FILE="${LOG_FILE:-$(dirname "$0")/github-commit-log.md}"
HOURS=6

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set." >&2
  exit 1
fi

NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SINCE=$(date -u -d "${HOURS} hours ago" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
  || date -u -v-${HOURS}H +%Y-%m-%dT%H:%M:%SZ)  # macOS fallback

# GitHub search API — searches default branch commits only
QUERY="user:${GITHUB_USER}+committer-date:>=${SINCE}"
URL="https://api.github.com/search/commits?q=${QUERY}&sort=committer-date&order=desc&per_page=100"

response=$(curl -s -H "Authorization: Bearer ${GITHUB_TOKEN}" \
                   -H "Accept: application/vnd.github+json" \
                   -H "X-GitHub-Api-Version: 2022-11-28" \
                   "$URL")

total=$(echo "$response" | jq '.total_count // 0')

# Build per-repo counts
declare -A repo_counts
while IFS= read -r repo; do
  repo_counts["$repo"]=$(( ${repo_counts["$repo"]:-0} + 1 ))
done < <(echo "$response" | jq -r '.items[].repository.full_name')

# Compose the markdown entry
{
  echo ""
  echo "## ${NOW} — window: ${SINCE} → ${NOW}"
  echo ""
  if [[ "$total" -eq 0 ]]; then
    echo "**Total commits: 0**"
    echo ""
    echo "No commits pushed to any ${GITHUB_USER} repository in this window."
  else
    echo "**Total commits: ${total}**"
    echo ""
    echo "| Repository | Commits |"
    echo "|---|---|"
    for repo in "${!repo_counts[@]}"; do
      echo "| \`${repo}\` | ${repo_counts[$repo]} |"
    done | sort
    if [[ "$total" -gt 100 ]]; then
      echo ""
      echo "> Note: GitHub search returns up to 100 results. Actual total: ${total}."
    fi
  fi
  echo ""
  echo "---"
} >> "$LOG_FILE"

echo "Logged ${total} commit(s) to ${LOG_FILE}"
