#!/usr/bin/env bash
# Check peak-flow/peaktrack for commits in the last 6 hours and append to commit-log.md
# Usage: ./scripts/check-commits.sh
# Requires: gh CLI authenticated, run from repo root

set -euo pipefail

OWNER="peak-flow"
REPO="peaktrack"
HOURS=6
LOG_FILE="$(dirname "$0")/../commit-log.md"

NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SINCE=$(date -u -d "${HOURS} hours ago" +%Y-%m-%dT%H:%M:%SZ)
WINDOW_LABEL="$(date -u -d "${HOURS} hours ago" +%H:%M) → $(date -u +%H:%M) UTC"
DATE_LABEL=$(date -u +%Y-%m-%d)

echo "Checking commits since ${SINCE}..."

# Get all branches
BRANCHES=$(gh api "repos/${OWNER}/${REPO}/branches" --paginate --jq '.[].name')

total_commits=0
table_rows=""

while IFS= read -r branch; do
    count=$(gh api "repos/${OWNER}/${REPO}/commits?sha=${branch}&since=${SINCE}&per_page=100" \
        --paginate --jq 'length' 2>/dev/null || echo 0)

    if [ "$count" -gt 0 ]; then
        total_commits=$((total_commits + count))
        # Get commit details for this branch
        commits_detail=$(gh api "repos/${OWNER}/${REPO}/commits?sha=${branch}&since=${SINCE}&per_page=100" \
            --jq '.[] | "| \(.sha[0:7]) | \(.commit.author.name) | \(.commit.message | split("\n")[0] | .[0:60]) |"' 2>/dev/null || true)
        table_rows+="**Branch: \`${branch}\`** (${count} commits)\n\n| SHA | Author | Message |\n|-----|--------|---------|\n${commits_detail}\n\n"
    fi
done <<< "$BRANCHES"

# Append to log file
{
    echo ""
    echo "## ${DATE_LABEL} $(date -u +%H:%M) UTC  _(window: ${WINDOW_LABEL})_"
    echo ""
    echo "**Repo:** ${OWNER}/${REPO}  |  **Total commits this window: ${total_commits}**"
    echo ""
    if [ "$total_commits" -eq 0 ]; then
        echo "> No commits detected in the last ${HOURS} hours."
    else
        echo "$table_rows"
    fi
    echo ""
    echo "---"
} >> "$LOG_FILE"

echo "Done. ${total_commits} commits logged to ${LOG_FILE}"
