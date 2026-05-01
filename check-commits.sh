#!/usr/bin/env bash
# Checks GitHub for commits in the last 6 hours and appends a summary to commit-log.md.
# Requires GITHUB_TOKEN to be set or stored in ~/.github_token_peaktrack.

set -euo pipefail

TOKEN_FILE="$HOME/.github_token_peaktrack"
if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  if [[ -f "$TOKEN_FILE" ]]; then
    GITHUB_TOKEN="$(cat "$TOKEN_FILE")"
  else
    echo "ERROR: GITHUB_TOKEN not set and $TOKEN_FILE not found." >&2
    exit 1
  fi
fi

LOG_FILE="$(dirname "$0")/commit-log.md"
REPOS=("peak-flow/peaktrack")
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SINCE=$(date -u -d '6 hours ago' +%Y-%m-%dT%H:%M:%SZ)
HUMAN_NOW=$(date -u '+%Y-%m-%d %H:%M UTC')

{
  echo ""
  echo "## $HUMAN_NOW"
  echo ""
  echo "| Repository | Commits (last 6h) |"
  echo "|------------|-------------------|"
} >> "$LOG_FILE"

TOTAL=0
for FULL_REPO in "${REPOS[@]}"; do
  OWNER="${FULL_REPO%%/*}"
  REPO="${FULL_REPO##*/}"

  # Paginate through all commits since SINCE
  COUNT=0
  PAGE=1
  while true; do
    RESULT=$(curl -s -w "\n%{http_code}" \
      -H "Authorization: Bearer $GITHUB_TOKEN" \
      -H "Accept: application/vnd.github+json" \
      "https://api.github.com/repos/$OWNER/$REPO/commits?since=$SINCE&per_page=100&page=$PAGE")
    HTTP_CODE=$(echo "$RESULT" | tail -1)
    BODY=$(echo "$RESULT" | head -n -1)

    if [[ "$HTTP_CODE" != "200" ]]; then
      echo "| $FULL_REPO | ERROR (HTTP $HTTP_CODE) |" >> "$LOG_FILE"
      break
    fi

    PAGE_COUNT=$(echo "$BODY" | grep -c '"sha"' || true)
    COUNT=$((COUNT + PAGE_COUNT))

    if [[ "$PAGE_COUNT" -lt 100 ]]; then
      echo "| \`$FULL_REPO\` | $COUNT |" >> "$LOG_FILE"
      TOTAL=$((TOTAL + COUNT))
      break
    fi
    PAGE=$((PAGE + 1))
  done
done

echo "" >> "$LOG_FILE"
echo "**Total commits:** $TOTAL" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
