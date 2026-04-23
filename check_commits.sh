#!/usr/bin/env bash
# Checks commits on peak-flow/peaktrack made in the last 6 hours and appends to commit_log.md

set -euo pipefail

REPO="peak-flow/peaktrack"
LOG_FILE="$(dirname "$0")/commit_log.md"
HOURS=6

# Token: set GITHUB_TOKEN in environment or ~/.bashrc
TOKEN="${GITHUB_TOKEN:-}"
if [[ -z "$TOKEN" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set. Export it before running." >&2
  exit 1
fi

NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SINCE=$(date -u -d "${HOURS} hours ago" +%Y-%m-%dT%H:%M:%SZ)
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M UTC")

# Fetch commits since the cutoff (up to 100)
RESPONSE=$(curl -sf \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${REPO}/commits?since=${SINCE}&per_page=100")

COUNT=$(echo "$RESPONSE" | jq 'length')

# Build the markdown entry
{
  echo ""
  echo "## ${TIMESTAMP}"
  echo ""
  echo "- **Repo**: \`${REPO}\`"
  echo "- **Commits in last ${HOURS}h**: ${COUNT}"
  echo ""
  if [[ "$COUNT" -gt 0 ]]; then
    echo "$RESPONSE" | jq -r '.[] | "- `\(.sha[0:7])` **\(.commit.author.name)** — \(.commit.message | split("\n")[0])"'
  else
    echo "_No commits in this window._"
  fi
} >> "$LOG_FILE"

echo "Appended ${COUNT} commit(s) to ${LOG_FILE}"
