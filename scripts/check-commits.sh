#!/usr/bin/env bash
# Checks peak-flow/peaktrack for commits in the last 6 hours and appends a
# summary to commit-log.md. Requires GITHUB_TOKEN to be set (or stored in
# ~/.config/peaktrack/github_token).

set -euo pipefail

OWNER="peak-flow"
REPO="peaktrack"
LOG_FILE="$(dirname "$0")/../commit-log.md"
TOKEN_FILE="$HOME/.config/peaktrack/github_token"

# --- Auth ---
if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  if [[ -f "$TOKEN_FILE" ]]; then
    GITHUB_TOKEN="$(cat "$TOKEN_FILE")"
  else
    echo "ERROR: Set GITHUB_TOKEN or create $TOKEN_FILE" >&2
    exit 1
  fi
fi

NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SINCE=$(date -u -d '6 hours ago' +%Y-%m-%dT%H:%M:%SZ)
WINDOW_LABEL="$(date -u -d '6 hours ago' +%H:%M) → $(date -u +%H:%M) UTC"
DATE_LABEL=$(date -u +%Y-%m-%d\ %H:%M\ UTC)

API="https://api.github.com/repos/$OWNER/$REPO"
AUTH_HEADER="Authorization: Bearer $GITHUB_TOKEN"
ACCEPT_HEADER="Accept: application/vnd.github+json"

# --- Fetch commits on default branch ---
COMMITS=$(curl -s -H "$AUTH_HEADER" -H "$ACCEPT_HEADER" \
  "$API/commits?since=$SINCE&until=$NOW&per_page=100")

COUNT=$(echo "$COMMITS" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data))" 2>/dev/null || echo 0)

# --- Build markdown entry ---
{
  echo "## $DATE_LABEL (window: $WINDOW_LABEL)"
  echo ""
  echo "**Total commits:** $COUNT"
  echo ""

  if [[ "$COUNT" -eq 0 ]]; then
    echo "No commits in this window."
  else
    echo "| SHA | Author | Message |"
    echo "|-----|--------|---------|"
    echo "$COMMITS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data:
    sha = c['sha'][:7]
    author = (c.get('author') or {}).get('login') or c['commit']['author']['name']
    msg = c['commit']['message'].split('\n')[0][:72]
    msg = msg.replace('|', '\\\\|')
    print(f'| \`{sha}\` | {author} | {msg} |')
"
  fi

  echo ""
  echo "---"
  echo ""
} >> "$LOG_FILE"

echo "Done. $COUNT commit(s) written to $LOG_FILE"
