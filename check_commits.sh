#!/usr/bin/env bash
set -euo pipefail

REPO_OWNER="peak-flow"
REPOS=("peaktrack")
LOG_FILE="$(dirname "$0")/github-commit-log.md"
TOKEN_FILE="$HOME/.config/peaktrack/github_token"

# Resolve token: env var takes precedence, then token file
if [ -n "${GITHUB_TOKEN:-}" ]; then
    TOKEN="$GITHUB_TOKEN"
elif [ -f "$TOKEN_FILE" ]; then
    TOKEN="$(cat "$TOKEN_FILE")"
else
    echo "ERROR: No GitHub token found. Set GITHUB_TOKEN or create $TOKEN_FILE" >&2
    exit 1
fi

SINCE=$(date -u -d '6 hours ago' +%Y-%m-%dT%H:%M:%SZ)
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
NOW_HUMAN=$(date -u '+%Y-%m-%d %H:%M UTC')

total_commits=0
declare -A repo_counts
declare -A repo_lines

for REPO in "${REPOS[@]}"; do
    page=1
    commit_lines=""
    count=0

    while true; do
        response=$(curl -sf \
            -H "Authorization: Bearer $TOKEN" \
            -H "Accept: application/vnd.github+json" \
            -H "X-GitHub-Api-Version: 2022-11-28" \
            "https://api.github.com/repos/$REPO_OWNER/$REPO/commits?since=$SINCE&per_page=100&page=$page" \
        || echo "[]")

        batch_count=$(echo "$response" | jq 'length')
        if [ "$batch_count" -eq 0 ]; then
            break
        fi

        while IFS= read -r line; do
            commit_lines+="$line"$'\n'
            count=$((count + 1))
        done < <(echo "$response" | jq -r '.[] | "  - \(.sha[0:7]): \(.commit.message | split("\n")[0]) by \(.commit.author.name)"')

        if [ "$batch_count" -lt 100 ]; then
            break
        fi
        page=$((page + 1))
    done

    repo_counts[$REPO]=$count
    repo_lines[$REPO]="$commit_lines"
    total_commits=$((total_commits + count))
done

# Build the markdown entry
entry="## $NOW_HUMAN — $total_commits commit(s) in last 6h"$'\n'
for REPO in "${REPOS[@]}"; do
    count=${repo_counts[$REPO]}
    entry+="- **$REPO_OWNER/$REPO** — $count commit(s)"$'\n'
    if [ "$count" -gt 0 ]; then
        entry+="${repo_lines[$REPO]}"
    fi
done
entry+=$'\n'

# Initialise the file with a header if it doesn't exist yet
if [ ! -f "$LOG_FILE" ]; then
    printf '# GitHub Commit Log\n\nChecks run every 6 hours. Tracking: %s/%s\n\n' \
        "$REPO_OWNER" "${REPOS[*]}" > "$LOG_FILE"
fi

printf '%s\n' "$entry" >> "$LOG_FILE"
echo "Logged $total_commits commit(s) since $SINCE → $LOG_FILE"
