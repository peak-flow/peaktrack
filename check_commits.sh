#!/bin/bash
# Checks commits on configured repos in the last 6 hours and appends to commit_log.md

REPOS=("peak-flow/peaktrack")
LOG_FILE="/home/user/peaktrack/commit_log.md"
SINCE=$(date -u -d '6 hours ago' '+%Y-%m-%dT%H:%M:%SZ')
NOW=$(date -u '+%Y-%m-%d %H:%M UTC')

if [ ! -f "$LOG_FILE" ]; then
    printf '# GitHub Commit Log\n\n' > "$LOG_FILE"
fi

printf '## Check: %s\n\n' "$NOW" >> "$LOG_FILE"

for REPO in "${REPOS[@]}"; do
    COUNT=$(curl -s \
        -H "Accept: application/vnd.github.v3+json" \
        ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
        "https://api.github.com/repos/$REPO/commits?since=$SINCE&per_page=100" \
        | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(len(data) if isinstance(data, list) else 0)
" 2>/dev/null || echo "0")

    echo "- **Repo:** \`$REPO\`" >> "$LOG_FILE"
    echo -e "- **Commits in last 6 hours:** $COUNT\n" >> "$LOG_FILE"
done

echo -e '---\n' >> "$LOG_FILE"
