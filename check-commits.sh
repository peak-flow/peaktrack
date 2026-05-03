#!/usr/bin/env bash
set -euo pipefail

REPO_OWNER="peak-flow"
REPO_NAME="peaktrack"
LOG_FILE="/home/user/peaktrack/commit-log.md"
SINCE=$(date -u -d '6 hours ago' +%Y-%m-%dT%H:%M:%SZ)
NOW_LABEL=$(date -u +"%Y-%m-%d %H:%M UTC")

# Fetch commits via GitHub API (requires GH_TOKEN or GITHUB_TOKEN)
TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
if [ -z "$TOKEN" ]; then
  echo "No GitHub token found (GH_TOKEN or GITHUB_TOKEN required)" >&2
  exit 1
fi

COUNT=$(curl -s \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/commits?since=${SINCE}&per_page=100" \
  | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data) if isinstance(data,list) else 0)")

# Append to log
{
  echo ""
  echo "## ${NOW_LABEL}"
  echo "- **${REPO_OWNER}/${REPO_NAME}**: ${COUNT} commits"
} >> "$LOG_FILE"

echo "Logged ${COUNT} commits for ${REPO_OWNER}/${REPO_NAME} at ${NOW_LABEL}"
