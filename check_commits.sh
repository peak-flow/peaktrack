#!/usr/bin/env bash
# Queries GitHub for commits in the last 6 hours across all accessible repos
# and appends a summary to commit_log.md

set -euo pipefail

GITHUB_TOKEN="${GITHUB_TOKEN:-}"
OUTPUT_FILE="$(dirname "$0")/commit_log.md"
HOURS=6

if [[ -z "$GITHUB_TOKEN" ]]; then
  echo "ERROR: GITHUB_TOKEN environment variable is not set." >&2
  exit 1
fi

SINCE=$(date -u -d "-${HOURS} hours" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null \
  || date -u -v-${HOURS}H '+%Y-%m-%dT%H:%M:%SZ')  # macOS fallback

NOW=$(date -u '+%Y-%m-%d %H:%M UTC')

# Fetch all repos the authenticated user has push access to (up to 100)
repos=$(curl -s \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/user/repos?per_page=100&sort=pushed&direction=desc" \
  | grep '"full_name"' \
  | sed 's/.*"full_name": *"\([^"]*\)".*/\1/')

declare -A repo_counts
total=0

for repo in $repos; do
  count=$(curl -s \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${repo}/commits?since=${SINCE}&per_page=100" \
    | grep -c '"sha"' || true)

  if [[ "$count" -gt 0 ]]; then
    repo_counts["$repo"]=$count
    total=$((total + count))
  fi
done

# Build markdown entry
{
  echo ""
  echo "## $NOW"
  echo ""
  echo "**Total commits in last ${HOURS}h:** $total"
  echo ""

  if [[ ${#repo_counts[@]} -eq 0 ]]; then
    echo "_No commits found._"
  else
    echo "| Repository | Commits |"
    echo "|------------|---------|"
    for repo in "${!repo_counts[@]}"; do
      echo "| \`$repo\` | ${repo_counts[$repo]} |"
    done
  fi

  echo ""
  echo "---"
} >> "$OUTPUT_FILE"

echo "[$NOW] Logged $total commit(s) across ${#repo_counts[@]} repo(s) → $OUTPUT_FILE"
