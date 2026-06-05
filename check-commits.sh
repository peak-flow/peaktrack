#!/usr/bin/env bash
# Fetches all peak-flow org commits from the last 6 hours and appends a
# dated section to commit-report.md.
# Requirements: curl, jq, GITHUB_TOKEN env var set.

set -euo pipefail

REPORT_FILE="$(dirname "$0")/commit-report.md"
HOURS=6
SINCE=$(date -u -d "${HOURS} hours ago" +"%Y-%m-%dT%H:%M:%SZ")
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
NOW_HUMAN=$(date -u +"%Y-%m-%d %H:%M UTC")

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "Error: GITHUB_TOKEN is not set." >&2
  exit 1
fi

echo "Checking commits since ${SINCE}..."

# Search commits across the org on default branches
RESPONSE=$(curl -s \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/search/commits?q=org:peak-flow+committer-date:>=${SINCE}&sort=committer-date&order=desc&per_page=100")

TOTAL=$(echo "$RESPONSE" | jq '.total_count')
echo "Found ${TOTAL} commits."

# Build per-repo table
REPO_TABLE=$(echo "$RESPONSE" | jq -r '
  [ .items[] | .repository.full_name ] |
  group_by(.) |
  map({ repo: .[0], count: length }) |
  sort_by(-.count) |
  .[] |
  "| \(.repo) | \(.count) |"
')

# Build commit detail list
COMMIT_DETAILS=$(echo "$RESPONSE" | jq -r '
  .items[] |
  "- **\(.repository.full_name)** — `\(.sha[:7])` \(.commit.message | split("\n")[0]) (\(.commit.author.name), \(.commit.author.date))"
')

# Append new section to the report
cat >> "${REPORT_FILE}" <<EOF

## ${NOW_HUMAN}
**Window:** ${SINCE} → ${NOW}
**Total commits in last ${HOURS}h:** ${TOTAL}

| Repo | Commits |
|------|---------|
${REPO_TABLE}

### Commit details
${COMMIT_DETAILS:-_No commits found._}

---
EOF

echo "Report updated: ${REPORT_FILE}"
