#!/usr/bin/env bash
# Queries GitHub API for commits in the last 6 hours and appends results to commit_activity_log.md

set -euo pipefail

REPOS=("peak-flow/peaktrack")
LOG_FILE="$(dirname "$0")/commit_activity_log.md"
TOKEN="${GITHUB_TOKEN:-}"

if [[ -z "$TOKEN" ]]; then
  echo "ERROR: GITHUB_TOKEN environment variable is not set." >&2
  exit 1
fi

SINCE=$(date -u -d '6 hours ago' '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null \
     || date -u -v-6H '+%Y-%m-%dT%H:%M:%SZ')  # macOS fallback
NOW=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

for REPO in "${REPOS[@]}"; do
  OWNER="${REPO%%/*}"
  NAME="${REPO##*/}"

  RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/$OWNER/$NAME/commits?since=$SINCE&per_page=100")

  HTTP_CODE=$(echo "$RESPONSE" | tail -1)
  BODY=$(echo "$RESPONSE" | head -n -1)

  if [[ "$HTTP_CODE" != "200" ]]; then
    echo "ERROR: GitHub API returned HTTP $HTTP_CODE for $REPO" >&2
    COUNT="ERROR($HTTP_CODE)"
  else
    COUNT=$(echo "$BODY" | jq 'length')
  fi

  echo "| $NOW | $REPO | $COUNT |" >> "$LOG_FILE"
  echo "Logged: $NOW | $REPO | $COUNT commits"
done
