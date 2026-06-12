#!/bin/bash
# Checks all peak-flow org repos for commits in the last 6 hours and appends a
# summary entry to commit-log.md. Designed to run in GitHub Actions.
set -euo pipefail

ORG="${ORG:-peak-flow}"
HOURS="${HOURS:-6}"
LOG_FILE="${LOG_FILE:-commit-log.md}"

SINCE=$(date -u -d "-${HOURS} hours" +%Y-%m-%dT%H:%M:%SZ)
NOW_LABEL=$(date -u +"%Y-%m-%d %H:%M UTC")

echo "Scanning ${ORG} for commits since ${SINCE}..."

# Only query repos that were pushed to recently (avoids 213 API calls).
# Sort by pushed_at descending; stop once pushed_at drops below $SINCE.
mapfile -t REPOS < <(
  gh api --paginate "orgs/${ORG}/repos?type=all&sort=pushed&direction=desc&per_page=100" \
    --jq --arg since "$SINCE" \
    '.[] | select(.pushed_at >= $since) | .name'
)

echo "Repos with recent pushes: ${#REPOS[@]}"

total=0
table_rows=""

for repo in "${REPOS[@]}"; do
  count=$(
    gh api --paginate "repos/${ORG}/${repo}/commits?since=${SINCE}&per_page=100" \
      --jq 'length' 2>/dev/null \
    | awk '{s+=$1} END {print s+0}'
  )
  if [[ "$count" -gt 0 ]]; then
    total=$((total + count))
    table_rows+="| ${repo} | ${count} |"$'\n'
    echo "  ${repo}: ${count} commit(s)"
  fi
done

# Build the markdown entry
{
  echo "## ${NOW_LABEL} — last ${HOURS}h"
  echo ""
  echo "**Total commits:** ${total}"
  echo ""
  if [[ -n "$table_rows" ]]; then
    echo "| Repository | Commits |"
    echo "| --- | --- |"
    printf '%s' "$table_rows"
  else
    echo "_No commits in the last ${HOURS} hours._"
  fi
  echo ""
  echo "---"
  echo ""
} > /tmp/new_entry.md

# Init log file with heading if it doesn't exist
if [[ ! -f "$LOG_FILE" ]]; then
  printf '# Commit Activity Log\n\n> Auto-updated every 6 hours by GitHub Actions.\n\n' > "$LOG_FILE"
fi

# Prepend the new entry below the first heading block (first 3 lines)
HEADER_LINES=3
head -n $HEADER_LINES "$LOG_FILE" > /tmp/log_new.md
cat /tmp/new_entry.md >> /tmp/log_new.md
tail -n +$((HEADER_LINES + 1)) "$LOG_FILE" >> /tmp/log_new.md
mv /tmp/log_new.md "$LOG_FILE"

echo "Done. ${total} total commits written to ${LOG_FILE}."
