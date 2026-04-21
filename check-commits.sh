#!/usr/bin/env bash
# Checks commits to peak-flow/peaktrack in the last 6 hours and appends a
# summary to commit-log.md. Requires GITHUB_TOKEN in the environment.

set -euo pipefail

OWNER="peak-flow"
REPOS=("peaktrack")
LOG_FILE="$(dirname "$0")/commit-log.md"
HOURS=6

NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SINCE=$(date -u -d "${HOURS} hours ago" +"%Y-%m-%dT%H:%M:%SZ")
NOW_LABEL=$(date -u +"%Y-%m-%d %H:%M UTC")

TOTAL=0
ENTRY="## ${NOW_LABEL}\n\n"

for REPO in "${REPOS[@]}"; do
    RESPONSE=$(curl -s \
        -H "Authorization: Bearer ${GITHUB_TOKEN}" \
        -H "Accept: application/vnd.github+json" \
        "https://api.github.com/repos/${OWNER}/${REPO}/commits?since=${SINCE}&until=${NOW}&per_page=100")

    COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data) if isinstance(data,list) else 0)" 2>/dev/null || echo 0)
    TOTAL=$((TOTAL + COUNT))

    ENTRY+="**Repo:** \`${OWNER}/${REPO}\`\n"
    ENTRY+="**Window:** ${SINCE} → ${NOW}\n"
    ENTRY+="**Total commits:** ${COUNT}\n\n"

    if [ "$COUNT" -gt 0 ]; then
        ENTRY+="| SHA | Author | Message |\n"
        ENTRY+="|-----|--------|---------|\n"
        while IFS= read -r line; do
            ENTRY+="${line}\n"
        done < <(echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if isinstance(data, list):
    for c in data:
        sha = c.get('sha','')[:7]
        author = (c.get('commit',{}).get('author') or {}).get('name','unknown')
        msg = (c.get('commit',{}).get('message','') or '').splitlines()[0][:80]
        print(f'| \`{sha}\` | {author} | {msg} |')
")
        ENTRY+="\n"
    else
        ENTRY+="_No commits in this window._\n\n"
    fi
done

ENTRY+="---\n"

printf "\n${ENTRY}" >> "$LOG_FILE"
echo "Done — ${TOTAL} total commit(s) logged to ${LOG_FILE}"
