#!/usr/bin/env bash
# Checks commits in the last 6 hours for peak-flow/peaktrack and appends to commit-log.md

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/../commit-log.md"
TOKEN_FILE="$SCRIPT_DIR/../.github_token"
TOKEN_ENV="${GITHUB_TOKEN:-}"

OWNER="peak-flow"
REPOS=("peaktrack")
HOURS=6

# Resolve token
if [[ -n "$TOKEN_ENV" ]]; then
    TOKEN="$TOKEN_ENV"
elif [[ -f "$TOKEN_FILE" ]]; then
    TOKEN="$(cat "$TOKEN_FILE" | tr -d '[:space:]')"
else
    echo "ERROR: No GitHub token found. Set GITHUB_TOKEN env var or create $TOKEN_FILE" >&2
    exit 1
fi

NOW_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SINCE_UTC=$(date -u -d "$HOURS hours ago" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
    || date -u -v"-${HOURS}H" +%Y-%m-%dT%H:%M:%SZ)  # macOS fallback

# Create log file with header if it doesn't exist
if [[ ! -f "$LOG_FILE" ]]; then
    cat > "$LOG_FILE" <<'HEADER'
# GitHub Commit Log

Automated log of commits per 6-hour window across tracked repositories.

---
HEADER
fi

# Build the new section
SECTION="## Check: $NOW_UTC\n\n"
SECTION+="**Window:** $SINCE_UTC → $NOW_UTC\n\n"
TOTAL_ALL=0

for REPO in "${REPOS[@]}"; do
    URL="https://api.github.com/repos/$OWNER/$REPO/commits?since=${SINCE_UTC}&per_page=100"
    RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" \
                        -H "Accept: application/vnd.github+json" \
                        -H "X-GitHub-Api-Version: 2022-11-28" \
                        "$URL")

    COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else 0)" 2>/dev/null || echo 0)
    TOTAL_ALL=$((TOTAL_ALL + COUNT))

    SECTION+="### \`$OWNER/$REPO\` — $COUNT commit(s)\n\n"

    if [[ "$COUNT" -gt 0 ]]; then
        COMMITS=$(echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if isinstance(data, list):
    for c in data:
        sha = c['sha'][:7]
        author = c['commit']['author']['name']
        msg = c['commit']['message'].split('\n')[0][:80]
        print(f'- \`{sha}\` **{author}**: {msg}')
" 2>/dev/null || echo "- (error parsing commits)")
        SECTION+="$COMMITS\n\n"
    else
        SECTION+="_No commits in this window._\n\n"
    fi
done

SECTION+="**Total across all repos:** $TOTAL_ALL commit(s)\n\n---\n"

# Append to log (insert after the header line "---")
printf "\n%b" "$SECTION" >> "$LOG_FILE"

echo "Done. $TOTAL_ALL commit(s) logged to $LOG_FILE"
