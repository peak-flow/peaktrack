#!/usr/bin/env bash
# Queries GitHub for all commits across the peak-flow org in the last 6 hours
# and appends a summary section to github-commit-log.md.
# Requires: gh CLI authenticated with repo + read:org scope, jq
set -euo pipefail

LOG_FILE="$(cd "$(dirname "$0")/.." && pwd)/github-commit-log.md"

NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SINCE=$(date -u -d '6 hours ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
        || date -u -v-6H +%Y-%m-%dT%H:%M:%SZ)

DATE_HEADER=$(date -u +"%Y-%m-%d %H:%M")
NOW_HMS=$(echo "$NOW"  | cut -c12-16)
SIN_HMS=$(echo "$SINCE" | cut -c12-16)

echo "Checking commits since ${SINCE} ..."

# GitHub commit search (needs Accept header for the commits preview endpoint)
RAW=$(gh api \
  -H "Accept: application/vnd.github.cloak-preview+json" \
  --paginate \
  "search/commits?q=org:peak-flow+committer-date:>=${SINCE}&sort=committer-date&order=desc&per_page=100" \
  2>/dev/null)

# When --paginate returns multiple JSON objects, merge the items arrays
ITEMS=$(echo "$RAW" | jq -s '[.[].items[]] | unique_by(.sha)')
TOTAL=$(echo "$ITEMS" | jq 'length')

echo "Found ${TOTAL} commit(s)."

# ── Build the markdown section ─────────────────────────────────────────────

SECTION="## ${DATE_HEADER} UTC  *(window: ${SIN_HMS} → ${NOW_HMS} UTC)*\n\n"

if [ "$TOTAL" -eq 0 ]; then
  SECTION+="**Total commits: 0**\n\nNo commits in this window."
else
  TABLE=$(echo "$ITEMS" | jq -r '
    group_by(.repository.full_name)
    | map({repo: .[0].repository.full_name, count: length})
    | sort_by(-.count)
    | .[]
    | "| \(.repo) | \(.count) |"
  ')

  SECTION+="**Total commits: ${TOTAL}**\n\n"
  SECTION+="| Repo | Commits |\n"
  SECTION+="|------|----------|\n"
  SECTION+="${TABLE}"
fi

SECTION+="\n\n---\n"

# ── Append to log file ─────────────────────────────────────────────────────

printf "\n%b" "$SECTION" >> "$LOG_FILE"

echo "Appended entry to ${LOG_FILE}"
