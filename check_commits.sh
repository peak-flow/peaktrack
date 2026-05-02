#!/usr/bin/env bash
# Checks peak-flow/peaktrack for commits in the last 6 hours and appends to commit_log.md.
# Requires GITHUB_TOKEN env var or a token stored in ~/.github_token

set -euo pipefail

REPO_OWNER="peak-flow"
REPO_NAME="peaktrack"
LOG_FILE="$(dirname "$0")/commit_log.md"
TOKEN="${GITHUB_TOKEN:-}"

if [[ -z "$TOKEN" && -f "$HOME/.github_token" ]]; then
  TOKEN="$(cat "$HOME/.github_token")"
fi

if [[ -z "$TOKEN" ]]; then
  echo "ERROR: No GitHub token found. Set GITHUB_TOKEN or write your token to ~/.github_token" >&2
  exit 1
fi

SINCE=$(date -u -d "6 hours ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
     || date -u -v-6H +"%Y-%m-%dT%H:%M:%SZ")  # macOS fallback
NOW=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

RESPONSE=$(curl -sf \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/commits?since=${SINCE}&per_page=100")

COUNT=$(echo "$RESPONSE" | jq 'length')

{
  echo "## ${NOW} - Commit Activity Report"
  echo "- **Repo**: ${REPO_OWNER}/${REPO_NAME}"
  echo "- **Commits in last 6 hours**: ${COUNT}"
  if [[ "$COUNT" -eq 0 ]]; then
    echo "- **Commit details**: *(no commits)*"
  else
    echo "- **Commit details**:"
    echo "$RESPONSE" | jq -r '.[] | "  - `\(.sha[0:7])` **\(.commit.author.name)**: \(.commit.message | split("\n")[0])"'
  fi
  echo ""
} >> "$LOG_FILE"

echo "Logged ${COUNT} commit(s) to ${LOG_FILE}"
