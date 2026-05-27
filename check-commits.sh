#!/usr/bin/env bash
# Checks commits across all peak-flow/peaktrack branches in the last 6 hours
# and appends a timestamped summary to commit-log.md.
#
# Usage:
#   export GITHUB_TOKEN=ghp_...
#   ./check-commits.sh
#
# To run every 6 hours via cron, add to crontab:
#   0 */6 * * * GITHUB_TOKEN=ghp_... /path/to/check-commits.sh

set -euo pipefail

GITHUB_TOKEN="${GITHUB_TOKEN:-}"
OWNER="peak-flow"
REPO="peaktrack"
OUTPUT_FILE="$(dirname "$0")/commit-log.md"
HOURS=6

if [[ -z "$GITHUB_TOKEN" ]]; then
  echo "Error: GITHUB_TOKEN is not set." >&2
  exit 1
fi

auth_header="Authorization: Bearer $GITHUB_TOKEN"
since=$(date -u -d "$HOURS hours ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
  || date -u -v-${HOURS}H +"%Y-%m-%dT%H:%M:%SZ")
now_label=$(date -u +"%Y-%m-%d %H:%M UTC")

# Fetch all branches
branches=$(curl -sf -H "$auth_header" \
  "https://api.github.com/repos/${OWNER}/${REPO}/branches?per_page=100" \
  | jq -r '.[].name')

declare -A repo_commits  # branch -> "sha|message" lines
total=0

for branch in $branches; do
  # URL-encode the branch name (/ -> %2F)
  encoded=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1],safe=''))" "$branch")
  raw=$(curl -sf -H "$auth_header" \
    "https://api.github.com/repos/${OWNER}/${REPO}/commits?sha=${encoded}&since=${since}&per_page=100" \
    2>/dev/null || echo "[]")
  count=$(echo "$raw" | jq 'length' 2>/dev/null || echo 0)
  if [[ "$count" -gt 0 ]]; then
    lines=$(echo "$raw" | jq -r '.[] | "- `\(.sha[0:7])` \(.commit.message | split("\n")[0])"')
    repo_commits["$branch"]="$lines"
    total=$((total + count))
  fi
done

# Create file with header if it doesn't exist
if [[ ! -f "$OUTPUT_FILE" ]]; then
  cat > "$OUTPUT_FILE" <<'HEADER'
# GitHub Commit Activity Log

Auto-generated every 6 hours. Tracks commits across `peak-flow/peaktrack` and all its branches.

---

HEADER
fi

{
  echo "## ${now_label}"
  echo ""
  echo "**Period:** last ${HOURS} hours (since \`${since}\`)"
  echo ""
  echo "**Total commits:** ${total}"
  echo ""
  if [[ ${#repo_commits[@]} -eq 0 ]]; then
    echo "_No commits across any checked branches in this period._"
  else
    for branch in $(echo "${!repo_commits[@]}" | tr ' ' '\n' | sort); do
      count=$(echo "${repo_commits[$branch]}" | grep -c '^-' || true)
      echo "### Branch: \`${branch}\` (${count} commit(s))"
      echo ""
      echo "${repo_commits[$branch]}"
      echo ""
    done
  fi
  echo "---"
  echo ""
} >> "$OUTPUT_FILE"

echo "Done. Total commits in last ${HOURS}h: ${total}"
