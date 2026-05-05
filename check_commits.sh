#!/usr/bin/env bash
# Checks peak-flow/peaktrack for commits in the last 6 hours and appends
# a summary entry to commit_log.md.
# Requires GITHUB_TOKEN to be set (or stored in ~/.github_token).

set -euo pipefail

OWNER="peak-flow"
REPO="peaktrack"
LOG_FILE="$(dirname "$0")/commit_log.md"
HOURS=6

# Load token from env or file
if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  if [[ -f "$HOME/.github_token" ]]; then
    GITHUB_TOKEN="$(cat "$HOME/.github_token")"
  else
    echo "ERROR: GITHUB_TOKEN not set and ~/.github_token not found" >&2
    exit 1
  fi
fi

API="https://api.github.com"
AUTH_HEADER="Authorization: Bearer $GITHUB_TOKEN"

NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SINCE=$(date -u -d "${HOURS} hours ago" +"%Y-%m-%dT%H:%M:%SZ")
NOW_DISPLAY=$(date -u +"%Y-%m-%d %H:%M UTC")
SINCE_DISPLAY=$(date -u -d "${HOURS} hours ago" +"%Y-%m-%d %H:%M UTC")

# Fetch all branches
BRANCHES=$(curl -sf -H "$AUTH_HEADER" \
  "$API/repos/$OWNER/$REPO/branches?per_page=100" \
  | python3 -c "import sys,json; [print(b['name']) for b in json.load(sys.stdin)]")

declare -A BRANCH_COUNTS
declare -A BRANCH_LATEST_MSG
declare -A BRANCH_LATEST_AUTHOR
declare -A BRANCH_LATEST_SHA

TOTAL=0
declare -A SEEN_SHAS

for BRANCH in $BRANCHES; do
  ENCODED_BRANCH=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$BRANCH")
  COMMITS=$(curl -sf -H "$AUTH_HEADER" \
    "$API/repos/$OWNER/$REPO/commits?sha=${ENCODED_BRANCH}&since=${SINCE}&per_page=100" || echo "[]")

  COUNT=$(echo "$COMMITS" | python3 -c "
import sys, json
commits = json.load(sys.stdin)
# deduplicate by SHA
seen = set()
unique = []
for c in commits:
    if c['sha'] not in seen:
        seen.add(c['sha'])
        unique.append(c)
print(len(unique))
print(unique[0]['commit']['message'].split('\n')[0] if unique else '')
print(unique[0]['author']['login'] if unique and unique[0].get('author') else 'unknown')
print(unique[0]['sha'][:8] if unique else '')
" 2>/dev/null || echo -e "0\n\n\n")

  N=$(echo "$COUNT" | sed -n '1p')
  MSG=$(echo "$COUNT" | sed -n '2p')
  AUTH=$(echo "$COUNT" | sed -n '3p')
  SHA=$(echo "$COUNT" | sed -n '4p')

  if [[ "$N" -gt 0 ]]; then
    BRANCH_COUNTS["$BRANCH"]=$N
    BRANCH_LATEST_MSG["$BRANCH"]="$MSG"
    BRANCH_LATEST_AUTHOR["$BRANCH"]="$AUTH"
    BRANCH_LATEST_SHA["$BRANCH"]="$SHA"
    TOTAL=$((TOTAL + N))
  fi
done

# Build markdown entry
{
  echo ""
  echo "## ${NOW_DISPLAY}  *(window: ${SINCE_DISPLAY} → ${NOW_DISPLAY})*"
  echo ""
  echo "**Total commits: ${TOTAL}**"
  echo ""

  if [[ $TOTAL -eq 0 ]]; then
    echo "_No commits in this window._"
  else
    echo "| Branch | Commits | Latest message | Author | SHA |"
    echo "|--------|---------|----------------|--------|-----|"
    for BRANCH in "${!BRANCH_COUNTS[@]}"; do
      echo "| ${BRANCH} | ${BRANCH_COUNTS[$BRANCH]} | ${BRANCH_LATEST_MSG[$BRANCH]} | ${BRANCH_LATEST_AUTHOR[$BRANCH]} | \`${BRANCH_LATEST_SHA[$BRANCH]}\` |"
    done
  fi

  echo ""
  echo "---"
} >> "$LOG_FILE"

echo "Done: $TOTAL commits found in the last ${HOURS}h. Appended to $LOG_FILE"
