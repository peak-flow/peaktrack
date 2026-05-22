#!/usr/bin/env bash
# Checks GitHub for commits in the last 6 hours and appends a report to commit-report.md

set -euo pipefail

REPORT_FILE="/home/user/peaktrack/commit-report.md"
REPOS=("peak-flow/peaktrack")

NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SINCE=$(date -u -d "6 hours ago" +"%Y-%m-%dT%H:%M:%SZ")
DISPLAY_NOW=$(date -u +"%Y-%m-%d %H:%M UTC")

# Create file with heading if it doesn't exist
if [ ! -f "$REPORT_FILE" ]; then
  cat > "$REPORT_FILE" <<'EOF'
# GitHub Commit Report

Auto-generated every 6 hours. Tracks commits across monitored repositories.

---
EOF
fi

# Build the report entry
ENTRY="## $DISPLAY_NOW\n\n"
ENTRY+="_Window: ${SINCE} to ${NOW}_\n\n"

GRAND_TOTAL=0

for REPO in "${REPOS[@]}"; do
  OWNER="${REPO%%/*}"
  REPONAME="${REPO##*/}"

  RESPONSE=$(curl -s \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$OWNER/$REPONAME/commits?since=$SINCE&per_page=100")

  COUNT=$(echo "$RESPONSE" | jq 'length')
  GRAND_TOTAL=$((GRAND_TOTAL + COUNT))

  ENTRY+="### \`$REPO\` — $COUNT commit(s)\n\n"

  if [ "$COUNT" -gt 0 ]; then
    while IFS= read -r line; do
      ENTRY+="$line\n"
    done < <(echo "$RESPONSE" | jq -r '.[] | "- `\(.sha[0:7])` **\(.commit.author.name)** — \(.commit.message | split("\n")[0]) (\(.commit.author.date))"')
  else
    ENTRY+="_No commits in this window._\n"
  fi

  ENTRY+="\n"
done

ENTRY+="**Total commits across all repos: $GRAND_TOTAL**\n\n---\n"

printf "$ENTRY" >> "$REPORT_FILE"
echo "Report updated: $GRAND_TOTAL commit(s) found across ${#REPOS[@]} repo(s) at $DISPLAY_NOW"
