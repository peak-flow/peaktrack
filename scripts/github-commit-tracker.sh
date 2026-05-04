#!/usr/bin/env bash
# Queries GitHub API for commits made in the last 6 hours across configured repos
# and appends a summary entry to commit-log.md.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/../commit-log.md"

# Add repos to track here as "owner/repo" entries
REPOS=(
  "peak-flow/peaktrack"
)

GITHUB_TOKEN="${GITHUB_TOKEN:-}"
if [[ -z "$GITHUB_TOKEN" ]]; then
  echo "Error: GITHUB_TOKEN environment variable is not set." >&2
  exit 1
fi

HOURS=6
SINCE=$(date -u -d "${HOURS} hours ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
  || date -u -v-"${HOURS}"H +"%Y-%m-%dT%H:%M:%SZ")  # macOS fallback

NOW=$(date -u +"%Y-%m-%d %H:%M UTC")
WINDOW_START=$(date -u -d "${HOURS} hours ago" +"%Y-%m-%d %H:%M UTC" 2>/dev/null \
  || date -u -v-"${HOURS}"H +"%Y-%m-%d %H:%M UTC")

TOTAL=0
declare -A REPO_COUNTS

for REPO in "${REPOS[@]}"; do
  PAGE=1
  COUNT=0
  while true; do
    RESPONSE=$(curl -sf \
      -H "Authorization: Bearer ${GITHUB_TOKEN}" \
      -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "https://api.github.com/repos/${REPO}/commits?since=${SINCE}&per_page=100&page=${PAGE}")

    BATCH=$(echo "$RESPONSE" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
    COUNT=$((COUNT + BATCH))

    if [[ "$BATCH" -lt 100 ]]; then
      break
    fi
    PAGE=$((PAGE + 1))
  done

  REPO_COUNTS["$REPO"]=$COUNT
  TOTAL=$((TOTAL + COUNT))
done

# Append entry to markdown log
{
  echo ""
  echo "## ${NOW}"
  echo ""
  echo "**Window:** ${WINDOW_START} → ${NOW}"
  echo ""
  echo "| Repository | Commits |"
  echo "|------------|---------|"
  for REPO in "${REPOS[@]}"; do
    echo "| \`${REPO}\` | ${REPO_COUNTS[$REPO]} |"
  done
  echo ""
  echo "**Total commits:** ${TOTAL}"
  echo ""
  echo "---"
} >> "$LOG_FILE"

echo "Logged ${TOTAL} commit(s) across ${#REPOS[@]} repo(s) → ${LOG_FILE}"
