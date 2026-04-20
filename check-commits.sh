#!/usr/bin/env bash
# Checks peak-flow/peaktrack for commits in the last 6 hours and appends to commit-tracker.md
# Requires: GITHUB_TOKEN env var with repo read access

set -euo pipefail

OWNER="peak-flow"
REPO="peaktrack"
TRACKER="/home/user/peaktrack/commit-tracker.md"
HOURS=6

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set" >&2
  exit 1
fi

NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SINCE=$(date -u -d "${HOURS} hours ago" +"%Y-%m-%dT%H:%M:%SZ")
LABEL=$(date -u +"%Y-%m-%d %H:%M UTC")

# Fetch all branches
BRANCHES=$(curl -sf \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${OWNER}/${REPO}/branches?per_page=100" \
  | grep '"name"' | sed 's/.*"name": "\(.*\)".*/\1/')

declare -A branch_commits
declare -A branch_authors
total=0

while IFS= read -r branch; do
  [[ -z "$branch" ]] && continue

  encoded_branch=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1],safe=''))" "$branch")

  response=$(curl -sf \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${OWNER}/${REPO}/commits?sha=${encoded_branch}&since=${SINCE}&per_page=100" \
    2>/dev/null || echo "[]")

  count=$(echo "$response" | grep -c '"sha"' || true)
  authors=$(echo "$response" | grep '"login"' | sed 's/.*"login": "\(.*\)".*/\1/' | sort -u | tr '\n' ',' | sed 's/,$//')

  if [[ $count -gt 0 ]]; then
    branch_commits["$branch"]=$count
    branch_authors["$branch"]=${authors:-unknown}
    total=$((total + count))
  fi
done <<< "$BRANCHES"

# Build markdown section
{
  echo ""
  echo "## ${LABEL}"
  echo ""
  if [[ $total -eq 0 ]]; then
    echo "| Branch | Commits (last ${HOURS}h) | Authors |"
    echo "|--------|:-----------------:|---------|"
    echo "| *(all branches checked)* | 0 | — |"
  else
    echo "| Branch | Commits (last ${HOURS}h) | Authors |"
    echo "|--------|:-----------------:|---------|"
    for branch in "${!branch_commits[@]}"; do
      echo "| \`${branch}\` | ${branch_commits[$branch]} | ${branch_authors[$branch]} |"
    done
  fi
  echo ""
  echo "**Total: ${total} commits** in window \`${SINCE} → ${NOW}\`"
} >> "$TRACKER"

echo "Done. ${total} new commits logged to ${TRACKER}"
