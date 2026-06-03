#!/usr/bin/env bash
set -euo pipefail

ORG="${GITHUB_ORG:-peak-flow}"
REPORTS_DIR="commit-reports"
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SINCE=$(date -u -d "6 hours ago" +"%Y-%m-%dT%H:%M:%SZ")
REPORT_FILE="${REPORTS_DIR}/$(date -u +"%Y-%m-%d-%H%M").md"

echo "Checking commits since $SINCE across org: $ORG"

mkdir -p "$REPORTS_DIR"

# Fetch all repos in the org (handles pagination)
repos=$(gh api "/orgs/${ORG}/repos" --paginate --jq '.[].full_name' 2>/dev/null || \
        gh api "/users/${ORG}/repos" --paginate --jq '.[].full_name')

total_commits=0
repo_lines=""

while IFS= read -r full_name; do
  repo_name="${full_name#*/}"
  count=$(gh api "/repos/${full_name}/commits?since=${SINCE}&per_page=100" \
    --paginate \
    --jq 'length' 2>/dev/null | paste -sd+ | bc 2>/dev/null || echo 0)

  if [[ "$count" -gt 0 ]]; then
    total_commits=$((total_commits + count))
    repo_lines+="| \`${full_name}\` | ${count} |"$'\n'
  fi
done <<< "$repos"

# Build the markdown report
{
  echo "# Commit Report"
  echo ""
  echo "**Period:** last 6 hours"
  echo "**From:** \`${SINCE}\`"
  echo "**To:** \`${NOW}\`"
  echo "**Org:** \`${ORG}\`"
  echo ""
  echo "## Summary"
  echo ""
  echo "**Total commits across all repos: ${total_commits}**"
  echo ""

  if [[ -n "$repo_lines" ]]; then
    echo "## Breakdown by Repository"
    echo ""
    echo "| Repository | Commits |"
    echo "|------------|---------|"
    echo -n "$repo_lines"
  else
    echo "> No commits found in the last 6 hours."
  fi
} > "$REPORT_FILE"

echo "Report written to $REPORT_FILE"
cat "$REPORT_FILE"
