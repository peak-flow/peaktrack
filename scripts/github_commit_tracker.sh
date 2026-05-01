#!/usr/bin/env bash
# Checks GitHub repos for commits in the last 6 hours and appends a report to a markdown file.
# Requires: GITHUB_TOKEN env var (or set TOKEN below), curl, jq
# Usage: ./github_commit_tracker.sh
# Cron:  0 */6 * * * /path/to/github_commit_tracker.sh

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
TOKEN="${GITHUB_TOKEN:-}"          # or hard-code your PAT here
REPOS=(
  "peak-flow/peaktrack"
  # add more repos here, e.g.:
  # "owner/repo-name"
)
REPORT_FILE="$(cd "$(dirname "$0")/.." && pwd)/commit_report.md"
HOURS=6
# ──────────────────────────────────────────────────────────────────────────────

if [[ -z "$TOKEN" ]]; then
  echo "Error: GITHUB_TOKEN is not set. Export it or hard-code TOKEN in the script." >&2
  exit 1
fi

if ! command -v jq &>/dev/null; then
  echo "Error: jq is required. Install with: sudo apt install jq  (or brew install jq)" >&2
  exit 1
fi

SINCE=$(date -u -d "-${HOURS} hours" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null \
     || date -u -v-"${HOURS}"H '+%Y-%m-%dT%H:%M:%SZ')  # macOS fallback
NOW=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
REPORT_DATE=$(date -u '+%Y-%m-%d %H:%M UTC')

TOTAL=0
SECTION=""

for REPO in "${REPOS[@]}"; do
  PAGE=1
  REPO_COUNT=0
  REPO_LINES=""

  while true; do
    RESPONSE=$(curl -sf \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "https://api.github.com/repos/${REPO}/commits?since=${SINCE}&until=${NOW}&per_page=100&page=${PAGE}")

    COUNT=$(echo "$RESPONSE" | jq 'length')
    [[ "$COUNT" -eq 0 ]] && break

    while IFS= read -r line; do
      REPO_LINES+="$line"$'\n'
    done < <(echo "$RESPONSE" | jq -r '.[] | "- [`\(.sha[0:7])`](https://github.com/'"${REPO}"'/commit/\(.sha)) \(.commit.message | split("\n")[0] | .[0:80]) — *\(.commit.author.name)* @ \(.commit.author.date)"')

    REPO_COUNT=$((REPO_COUNT + COUNT))
    [[ "$COUNT" -lt 100 ]] && break
    PAGE=$((PAGE + 1))
  done

  TOTAL=$((TOTAL + REPO_COUNT))
  SECTION+="### \`${REPO}\` — ${REPO_COUNT} commit(s)"$'\n\n'
  if [[ "$REPO_COUNT" -gt 0 ]]; then
    SECTION+="${REPO_LINES}"
  else
    SECTION+="_No commits in this window._"$'\n'
  fi
  SECTION+=$'\n'
done

# Append to the markdown report
{
  echo "## ${REPORT_DATE} — ${TOTAL} total commit(s) in last ${HOURS}h"
  echo ""
  echo "$SECTION"
  echo "---"
  echo ""
} >> "$REPORT_FILE"

echo "Report updated: ${REPORT_FILE} (${TOTAL} commits across ${#REPOS[@]} repo(s))"
