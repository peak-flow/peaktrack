#!/usr/bin/env bash
# Queries GitHub for commits in the last 6 hours and appends a report to commit-activity.md.
# Requires GITHUB_TOKEN env var (Personal Access Token with repo:read scope).

set -euo pipefail

REPOS=("peak-flow/peaktrack")
OUTPUT_FILE="$(dirname "$0")/commit-activity.md"
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SINCE=$(date -u -d "6 hours ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
  || date -u -v-6H +"%Y-%m-%dT%H:%M:%SZ")  # macOS fallback
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M")

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set. Export a GitHub Personal Access Token." >&2
  exit 1
fi

TOTAL=0
LINES=()

for REPO in "${REPOS[@]}"; do
  OWNER="${REPO%%/*}"
  REPO_NAME="${REPO##*/}"

  # Fetch commits since SINCE via GitHub REST API (up to 100 per page)
  RESPONSE=$(curl -sf \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/${OWNER}/${REPO_NAME}/commits?since=${SINCE}&per_page=100" \
    || echo "[]")

  COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data) if isinstance(data,list) else 0)")
  TOTAL=$((TOTAL + COUNT))

  LINES+=("- **${REPO}**: ${COUNT} commits")

  if [[ "$COUNT" -gt 0 ]]; then
    COMMIT_LINES=$(echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data:
    sha = c['sha'][:7]
    msg = c['commit']['message'].split('\n')[0][:80]
    print(f'  - {sha}: {msg}')
")
    while IFS= read -r line; do
      LINES+=("$line")
    done <<< "$COMMIT_LINES"
  fi
done

REPO_COUNT="${#REPOS[@]}"

{
  echo "## ${TIMESTAMP} UTC"
  echo ""
  for line in "${LINES[@]}"; do
    echo "$line"
  done
  echo ""
  echo "**Total: ${TOTAL} commits across ${REPO_COUNT} repo(s)**"
  echo ""
  echo "---"
  echo ""
} >> "$OUTPUT_FILE"

echo "Done. ${TOTAL} commits logged to ${OUTPUT_FILE}"
