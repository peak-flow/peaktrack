#!/usr/bin/env bash
# Checks commits in the last 6 hours for repos under peak-flow org and appends a summary to commit-activity.md

set -euo pipefail

GITHUB_TOKEN="${GITHUB_TOKEN:-}"
ORG="peak-flow"
OUTPUT_FILE="$(dirname "$0")/commit-activity.md"
HOURS=6

if [[ -z "$GITHUB_TOKEN" ]]; then
  echo "Error: GITHUB_TOKEN is not set." >&2
  exit 1
fi

auth_header="Authorization: Bearer $GITHUB_TOKEN"
since=$(date -u -d "$HOURS hours ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -v-${HOURS}H +"%Y-%m-%dT%H:%M:%SZ")
now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

repos=$(curl -sf -H "$auth_header" \
  "https://api.github.com/orgs/${ORG}/repos?per_page=100&type=all" \
  | jq -r '.[].name')

declare -A repo_counts
total=0

for repo in $repos; do
  count=$(curl -sf -H "$auth_header" \
    "https://api.github.com/repos/${ORG}/${repo}/commits?since=${since}&per_page=100" \
    | jq 'length' 2>/dev/null || echo 0)
  if [[ "$count" -gt 0 ]]; then
    repo_counts["$repo"]="$count"
    total=$((total + count))
  fi
done

# Create file with header if it doesn't exist
if [[ ! -f "$OUTPUT_FILE" ]]; then
  cat > "$OUTPUT_FILE" <<'HEADER'
# GitHub Commit Activity

Auto-generated every 6 hours. Tracks commits across `peak-flow` repositories.

---

HEADER
fi

# Append new entry
{
  echo "## $(date -u +"%Y-%m-%d %H:%M UTC")"
  echo ""
  echo "**Period:** last ${HOURS} hours (since \`${since}\`)"
  echo ""
  echo "**Total commits:** ${total}"
  echo ""
  if [[ ${#repo_counts[@]} -eq 0 ]]; then
    echo "_No commits in this period._"
  else
    echo "| Repository | Commits |"
    echo "|---|---|"
    for repo in $(echo "${!repo_counts[@]}" | tr ' ' '\n' | sort); do
      echo "| \`${ORG}/${repo}\` | ${repo_counts[$repo]} |"
    done
  fi
  echo ""
  echo "---"
  echo ""
} >> "$OUTPUT_FILE"

echo "Done. Total commits in last ${HOURS}h: ${total}"
