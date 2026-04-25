#!/usr/bin/env bash
# Queries GitHub API for commits made in the last 6 hours across all accessible
# repos for the configured owner, then appends a report to commit_report.md.

set -euo pipefail

GITHUB_TOKEN="${GITHUB_TOKEN:-}"
GITHUB_OWNER="${GITHUB_OWNER:-peak-flow}"
OUTPUT_FILE="${OUTPUT_FILE:-$(dirname "$0")/commit_report.md}"
HOURS="${HOURS:-6}"

if [[ -z "$GITHUB_TOKEN" ]]; then
  echo "ERROR: GITHUB_TOKEN environment variable is not set." >&2
  echo "Export it before running: export GITHUB_TOKEN=ghp_..." >&2
  exit 1
fi

SINCE=$(date -u -d "-${HOURS} hours" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
  || date -u -v-"${HOURS}"H +"%Y-%m-%dT%H:%M:%SZ")  # macOS fallback
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

AUTH_HEADER="Authorization: Bearer $GITHUB_TOKEN"
API="https://api.github.com"

fetch_json() {
  curl -sSf -H "$AUTH_HEADER" -H "Accept: application/vnd.github+json" "$@"
}

# Fetch up to 100 repos for the owner (handles orgs and users)
REPOS_JSON=$(fetch_json "$API/orgs/$GITHUB_OWNER/repos?per_page=100&sort=pushed" 2>/dev/null \
  || fetch_json "$API/users/$GITHUB_OWNER/repos?per_page=100&sort=pushed")

REPO_NAMES=$(echo "$REPOS_JSON" | grep -o '"name":"[^"]*"' | sed 's/"name":"//;s/"//')

declare -A REPO_COUNTS
TOTAL=0

for REPO in $REPO_NAMES; do
  COMMITS_JSON=$(fetch_json \
    "$API/repos/$GITHUB_OWNER/$REPO/commits?since=${SINCE}&until=${NOW}&per_page=100" \
    2>/dev/null || echo "[]")

  COUNT=$(echo "$COMMITS_JSON" | grep -c '"sha"' || true)

  if [[ "$COUNT" -gt 0 ]]; then
    REPO_COUNTS["$REPO"]=$COUNT
    TOTAL=$((TOTAL + COUNT))
  fi
done

# ── Write / append report ────────────────────────────────────────────────────

{
  echo ""
  echo "## Report: $NOW"
  echo ""
  echo "**Window:** last ${HOURS} hours (since \`${SINCE}\`)"
  echo ""
  echo "**Total commits:** $TOTAL"
  echo ""

  if [[ "$TOTAL" -eq 0 ]]; then
    echo "_No commits found in this window._"
  else
    echo "| Repository | Commits |"
    echo "|------------|---------|"
    for REPO in "${!REPO_COUNTS[@]}"; do
      echo "| \`$GITHUB_OWNER/$REPO\` | ${REPO_COUNTS[$REPO]} |"
    done | sort -t'|' -k3 -rn
  fi

  echo ""
  echo "---"
} >> "$OUTPUT_FILE"

echo "Report appended to $OUTPUT_FILE  (total: $TOTAL commits across ${#REPO_COUNTS[@]} repos)"
