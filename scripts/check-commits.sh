#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="/home/user/peaktrack/commit-log.md"
REPOS=("peak-flow/peaktrack")
SINCE=$(date -u -d '6 hours ago' +%Y-%m-%dT%H:%M:%SZ)
NOW=$(date -u +"%Y-%m-%d %H:%M UTC")

AUTH_HEADER=""
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    AUTH_HEADER="Authorization: Bearer ${GITHUB_TOKEN}"
elif [[ -f "$HOME/.config/peaktrack/github_token" ]]; then
    TOKEN=$(cat "$HOME/.config/peaktrack/github_token")
    AUTH_HEADER="Authorization: Bearer ${TOKEN}"
fi

api_get() {
    local url="$1"
    if [[ -n "$AUTH_HEADER" ]]; then
        curl -sf -H "$AUTH_HEADER" -H "Accept: application/vnd.github+json" "$url"
    else
        curl -sf -H "Accept: application/vnd.github+json" "$url"
    fi
}

count_commits() {
    local owner="$1"
    local repo="$2"
    local url="https://api.github.com/repos/${owner}/${repo}/commits?since=${SINCE}&per_page=100"
    local result
    result=$(api_get "$url") || { echo "0"; return; }
    echo "$result" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data))" 2>/dev/null || echo "0"
}

# Build table rows
TABLE_ROWS=""
TOTAL=0
for REPO in "${REPOS[@]}"; do
    OWNER="${REPO%%/*}"
    NAME="${REPO##*/}"
    COUNT=$(count_commits "$OWNER" "$NAME")
    TABLE_ROWS+="| ${REPO} | ${COUNT} |\n"
    TOTAL=$((TOTAL + COUNT))
done

# Append to log file
{
    echo "## ${NOW}"
    echo ""
    echo "| Repository | Commits (last 6h) |"
    echo "|---|---|"
    printf "%b" "$TABLE_ROWS"
    echo ""
    echo "**Total:** ${TOTAL} commits"
    echo ""
    echo "---"
    echo ""
} >> "$LOG_FILE"

echo "Logged ${TOTAL} commits at ${NOW}"
