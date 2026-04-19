#!/usr/bin/env bash
# Fetches commits from the last 6 hours for monitored repos and appends to github_commit_log.md.
# Requires: curl, jq
# Usage: GITHUB_TOKEN=your_token ./check_commits.sh
#        or export GITHUB_TOKEN before running

set -euo pipefail

REPOS=("peak-flow/peaktrack")
LOG_FILE="$(dirname "$0")/github_commit_log.md"
HOURS=6
SINCE=$(date -u -d "${HOURS} hours ago" +"%Y-%m-%dT%H:%M:%SZ")
NOW=$(date -u +"%Y-%m-%d %H:%M UTC")

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "Error: GITHUB_TOKEN is not set." >&2
  exit 1
fi

total_commits=0
report_lines=()

for repo in "${REPOS[@]}"; do
  owner="${repo%%/*}"
  name="${repo##*/}"

  response=$(curl -sf \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${owner}/${name}/commits?since=${SINCE}&per_page=100" \
  ) || { echo "Warning: failed to fetch ${repo}" >&2; continue; }

  count=$(echo "$response" | jq 'length')
  total_commits=$((total_commits + count))

  report_lines+=("- **Repo**: ${repo} — ${count} commits")

  if [[ "$count" -gt 0 ]]; then
    while IFS= read -r line; do
      report_lines+=("  - ${line}")
    done < <(echo "$response" | jq -r '.[] | "\(.sha[0:7]): \(.commit.message | split("\n")[0]) (\(.commit.author.name))"')
  fi
done

repo_count=${#REPOS[@]}

{
  echo "## ${NOW} - Commit Report (last ${HOURS} hours)"
  echo ""
  for line in "${report_lines[@]}"; do
    echo "$line"
  done
  echo ""
  echo "**Total**: ${total_commits} commits across ${repo_count} repo(s)"
  echo ""
  echo "---"
  echo ""
} >> "$LOG_FILE"

echo "Done. ${total_commits} commit(s) logged to ${LOG_FILE}"
