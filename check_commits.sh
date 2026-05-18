#!/usr/bin/env bash
# Checks GitHub for commits in the last 6 hours and appends results to commit_activity_log.md
set -euo pipefail

LOG_FILE="$(dirname "$0")/commit_activity_log.md"
REPOS=("peak-flow/peaktrack")
HOURS=6

now_ts=$(date -u +%s)
since_ts=$((now_ts - HOURS * 3600))
since_iso=$(date -u -d "@$since_ts" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
            || date -u -r "$since_ts" +%Y-%m-%dT%H:%M:%SZ)  # macOS fallback
now_iso=$(date -u +%Y-%m-%dT%H:%M:%SZ)

total=0
table_rows=""

for repo in "${REPOS[@]}"; do
    owner="${repo%%/*}"
    name="${repo##*/}"
    url="https://api.github.com/repos/${owner}/${name}/commits?since=${since_iso}&per_page=100"

    response=$(curl -s -H "Accept: application/vnd.github+json" \
        ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
        "$url" || echo "[]")

    count=$(echo "$response" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data) if isinstance(data,list) else 0)" 2>/dev/null || echo 0)
    total=$((total + count))
    table_rows+="| \`${repo}\` | ${count} |"$'\n'
done

# Create file with header if it doesn't exist
if [ ! -f "$LOG_FILE" ]; then
    cat > "$LOG_FILE" <<'EOF'
# GitHub Commit Activity Log

Checked every 6 hours. Each entry covers the preceding 6-hour window.

---

EOF
fi

# Append new entry
cat >> "$LOG_FILE" <<EOF
## $(date -u +"%Y-%m-%d %H:%M UTC")

**Window:** \`${since_iso}\` → \`${now_iso}\`

| Repository | Commits |
|------------|---------|
${table_rows}
**Total commits:** ${total}

---

EOF

echo "LOGGED|$(date -u +%Y-%m-%dT%H:%M:%SZ)|total=${total}|window=${since_iso}/${now_iso}"
