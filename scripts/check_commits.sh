#!/usr/bin/env bash
# Checks GitHub for commits in the last 6 hours and appends a summary to commit_log.md.
# Requires GITHUB_TOKEN env var or a token stored in ~/.github_token.

set -euo pipefail

REPOS=("peak-flow/peaktrack")
LOG_FILE="/home/user/peaktrack/commit_log.md"
HOURS=6

# Load token from env or file
if [ -z "${GITHUB_TOKEN:-}" ]; then
  TOKEN_FILE="$HOME/.github_token"
  if [ -f "$TOKEN_FILE" ]; then
    GITHUB_TOKEN=$(cat "$TOKEN_FILE")
  else
    echo "ERROR: GITHUB_TOKEN not set and $TOKEN_FILE not found." >&2
    exit 1
  fi
fi

SINCE=$(date -u -d "$HOURS hours ago" +"%Y-%m-%dT%H:%M:%SZ")
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
NOW_HUMAN=$(date -u +"%Y-%m-%d %H:%M UTC")

# Initialise log file with header if it doesn't exist
if [ ! -f "$LOG_FILE" ]; then
  cat > "$LOG_FILE" <<'HEADER'
# GitHub Commit Log

Automated 6-hour commit summary for tracked repositories.

---

HEADER
fi

{
  echo "## $NOW_HUMAN"
  echo ""
  echo "| Repository | Commits (last 6h) |"
  echo "|------------|-------------------|"

  TOTAL=0
  for REPO in "${REPOS[@]}"; do
    OWNER="${REPO%%/*}"
    REPO_NAME="${REPO##*/}"

    COUNT=$(curl -s \
      -H "Authorization: Bearer $GITHUB_TOKEN" \
      -H "Accept: application/vnd.github+json" \
      "https://api.github.com/repos/$OWNER/$REPO_NAME/commits?since=$SINCE&per_page=100" \
      | jq 'if type == "array" then length else 0 end')

    echo "| \`$REPO\` | $COUNT |"
    TOTAL=$((TOTAL + COUNT))
  done

  echo ""
  echo "**Total commits:** $TOTAL  "
  echo "**Period:** $SINCE → $NOW"
  echo ""
  echo "---"
  echo ""
} >> "$LOG_FILE"

echo "Logged $TOTAL commit(s) across ${#REPOS[@]} repo(s) at $NOW_HUMAN"
