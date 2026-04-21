#!/usr/bin/env bash
# Checks GitHub repos for commits in the last 6 hours and appends a summary to a markdown file.
# Usage: ./check_commits.sh [REPOS...]
# Requires: GITHUB_TOKEN env var, jq, curl

set -euo pipefail

REPORT_FILE="${REPORT_FILE:-/home/user/peaktrack/commit_report.md}"
HOURS="${HOURS:-6}"

# Default repos to check — space-separated "owner/repo" values
DEFAULT_REPOS=("peak-flow/peaktrack")
REPOS=("${@:-${DEFAULT_REPOS[@]}}")

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set. Export it before running this script." >&2
  exit 1
fi

# ISO-8601 timestamp for 6 hours ago
SINCE=$(date -u -d "${HOURS} hours ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
        || date -u -v "-${HOURS}H" +"%Y-%m-%dT%H:%M:%SZ")  # macOS fallback

NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
RUN_TS=$(date -u +"%Y-%m-%d %H:%M UTC")

declare -A REPO_COUNTS
TOTAL=0
ANY_ERROR=0

for REPO in "${REPOS[@]}"; do
  PAGE=1
  COUNT=0
  while true; do
    RESPONSE=$(curl -sf \
      -H "Authorization: Bearer ${GITHUB_TOKEN}" \
      -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "https://api.github.com/repos/${REPO}/commits?since=${SINCE}&per_page=100&page=${PAGE}" \
      2>&1) || { echo "WARN: Failed to fetch ${REPO} page ${PAGE}" >&2; ANY_ERROR=1; break; }

    PAGE_COUNT=$(echo "$RESPONSE" | jq 'length' 2>/dev/null || echo 0)
    COUNT=$((COUNT + PAGE_COUNT))

    # Stop paginating when a page returns fewer than 100 items
    if [[ "$PAGE_COUNT" -lt 100 ]]; then
      break
    fi
    PAGE=$((PAGE + 1))
  done

  REPO_COUNTS["$REPO"]=$COUNT
  TOTAL=$((TOTAL + COUNT))
done

# ── Write report section ─────────────────────────────────────────────────────

# Create file with header if it doesn't exist yet
if [[ ! -f "$REPORT_FILE" ]]; then
  cat > "$REPORT_FILE" <<'HEADER'
# GitHub Commit Activity Report

Auto-generated every 6 hours. Each section covers the preceding 6-hour window.

---

HEADER
fi

{
  echo "## ${RUN_TS}"
  echo ""
  echo "**Window:** ${SINCE} → ${NOW}"
  echo ""
  echo "| Repository | Commits |"
  echo "|------------|---------|"
  for REPO in "${REPOS[@]}"; do
    echo "| \`${REPO}\` | ${REPO_COUNTS[$REPO]:-0} |"
  done
  echo ""
  echo "**Total commits:** ${TOTAL}"
  [[ "$ANY_ERROR" -eq 1 ]] && echo "" && echo "> ⚠️ One or more repos could not be fetched — counts may be incomplete."
  echo ""
  echo "---"
  echo ""
} >> "$REPORT_FILE"

echo "Report updated: ${REPORT_FILE} (${TOTAL} commit(s) across ${#REPOS[@]} repo(s))"
