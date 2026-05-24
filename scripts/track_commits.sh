#!/usr/bin/env bash
set -euo pipefail

# Repos to track — add more "owner/repo" entries here, one per line
REPOS=(
  "peak-flow/peaktrack"
)

SINCE=$(date -u -d '6 hours ago' '+%Y-%m-%dT%H:%M:%SZ')
NOW=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
REPORT_DATE=$(date -u '+%Y-%m-%d')
REPORT_HOUR=$(date -u '+%H')
REPORT_FILE="commit-reports/${REPORT_DATE}-${REPORT_HOUR}00-UTC.md"
SUMMARY_FILE="commit-reports/SUMMARY.md"

total_commits=0
declare -A repo_counts

echo "Checking commits since ${SINCE} ..."

for REPO in "${REPOS[@]}"; do
  count=$(gh api \
    --paginate \
    -H "Accept: application/vnd.github+json" \
    "/repos/${REPO}/commits?since=${SINCE}&per_page=100" \
    --jq 'length' | \
    awk '{s+=$1} END {print s+0}')

  repo_counts["$REPO"]=$count
  total_commits=$((total_commits + count))
  echo "  ${REPO}: ${count} commit(s)"
done

# ── Write timestamped report ────────────────────────────────────────────────
mkdir -p commit-reports

{
  echo "# Commit Report — ${REPORT_DATE} ${REPORT_HOUR}:00 UTC"
  echo ""
  echo "> Window: \`${SINCE}\` → \`${NOW}\`"
  echo ""
  echo "## Summary"
  echo ""
  echo "| Repository | Commits |"
  echo "|---|---|"
  for REPO in "${REPOS[@]}"; do
    echo "| \`${REPO}\` | ${repo_counts[$REPO]} |"
  done
  echo ""
  echo "**Total: ${total_commits} commit(s)**"
} > "$REPORT_FILE"

echo "Report written to ${REPORT_FILE}"

# ── Update rolling SUMMARY.md ───────────────────────────────────────────────
HEADER="# Commit Tracker — Rolling Summary"

# Create file with header if it doesn't exist
if [[ ! -f "$SUMMARY_FILE" ]]; then
  {
    echo "$HEADER"
    echo ""
    echo "| Timestamp (UTC) | Repository | Commits in window |"
    echo "|---|---|---|"
  } > "$SUMMARY_FILE"
fi

for REPO in "${REPOS[@]}"; do
  echo "| ${REPORT_DATE} ${REPORT_HOUR}:00 | \`${REPO}\` | ${repo_counts[$REPO]} |" >> "$SUMMARY_FILE"
done

echo "Summary updated at ${SUMMARY_FILE}"
