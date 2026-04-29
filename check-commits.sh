#!/usr/bin/env bash
# Checks commits in the last 6 hours across tracked repos and appends to commit-tracker.md

set -euo pipefail

TRACKER="/home/user/peaktrack/commit-tracker.md"
TOKEN="${GITHUB_TOKEN:-}"
REPOS=("peak-flow/peaktrack")

if [[ -z "$TOKEN" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set" >&2
  exit 1
fi

SINCE=$(date -u -d '6 hours ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
  || date -u -v-6H +%Y-%m-%dT%H:%M:%SZ)  # macOS fallback
NOW=$(date -u +"%Y-%m-%d %H:%M UTC")

# Build the summary table and per-repo detail sections
TABLE_ROWS=""
DETAIL_SECTIONS=""

for REPO in "${REPOS[@]}"; do
  OWNER="${REPO%%/*}"
  NAME="${REPO##*/}"

  COMMITS=$(curl -sf \
    -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$OWNER/$NAME/commits?since=$SINCE&per_page=100" \
    || echo "[]")

  COUNT=$(echo "$COMMITS" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data))" 2>/dev/null || echo 0)
  TABLE_ROWS+="| $REPO | $COUNT |"$'\n'

  DETAIL_SECTIONS+="### $REPO"$'\n'
  if [[ "$COUNT" -eq 0 ]]; then
    DETAIL_SECTIONS+=$'\n'"No commits in this window."$'\n\n'
  else
    DETAIL_SECTIONS+=$'\n'"| SHA | Author | Message | Time |"$'\n'
    DETAIL_SECTIONS+="| --- | ------ | ------- | ---- |"$'\n'
    DETAIL_SECTIONS+=$(echo "$COMMITS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data:
    sha = c['sha'][:7]
    author = (c.get('commit', {}).get('author') or {}).get('name', 'unknown')
    msg = (c.get('commit', {}).get('message') or '').splitlines()[0][:72]
    ts = (c.get('commit', {}).get('author') or {}).get('date', '')[:16].replace('T',' ')
    print(f'| {sha} | {author} | {msg} | {ts} |')
" 2>/dev/null || echo "| (parse error) | | | |")
    DETAIL_SECTIONS+=$'\n\n'
  fi
done

# Append new section to the tracker file
cat >> "$TRACKER" <<EOF

## $NOW — last 6 hours

| Repo | Commits |
|------|---------|
${TABLE_ROWS}
${DETAIL_SECTIONS}---

EOF

echo "Done: $NOW"
