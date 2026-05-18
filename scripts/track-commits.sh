#!/bin/bash
set -euo pipefail

SINCE=$(date -u -d '6 hours ago' '+%Y-%m-%dT%H:%M:%SZ')
WINDOW_START=$(date -u -d '6 hours ago' '+%Y-%m-%d %H:%M UTC')
WINDOW_END=$(date -u '+%Y-%m-%d %H:%M UTC')
DATE=$(date -u '+%Y-%m-%d')
REPORT_DIR="commit-reports"
REPORT_FILE="$REPORT_DIR/$DATE.md"

mkdir -p "$REPORT_DIR"

# Create file header if it doesn't exist yet
if [ ! -f "$REPORT_FILE" ]; then
  echo "# Commit Report — $DATE" > "$REPORT_FILE"
  echo "" >> "$REPORT_FILE"
fi

# Determine which repos to check.
# If a COMMIT_TRACKER_TOKEN secret is set with broader access,
# it will query all repos the token owner has access to.
# Otherwise falls back to just this repo.
if [ -n "${COMMIT_TRACKER_TOKEN:-}" ] && [ "${COMMIT_TRACKER_TOKEN}" != "${GITHUB_TOKEN:-}" ]; then
  echo "Using COMMIT_TRACKER_TOKEN — fetching all accessible repos..."
  REPOS=$(gh api user/repos --paginate -f per_page=100 --jq '.[].full_name' 2>/dev/null || echo "peak-flow/peaktrack")
else
  REPOS="${GITHUB_REPOSITORY:-peak-flow/peaktrack}"
fi

# Append a new time-window section to today's report
{
  echo "## $WINDOW_START → $WINDOW_END"
  echo ""
} >> "$REPORT_FILE"

TOTAL=0
HAS_COMMITS=false

while IFS= read -r REPO; do
  [ -z "$REPO" ] && continue

  # Fetch commits since SINCE; --paginate merges all pages into one array
  RAW=$(gh api "repos/$REPO/commits?since=$SINCE&per_page=100" --paginate 2>/dev/null || echo "[]")

  # Guard against error responses (non-array JSON)
  COUNT=$(echo "$RAW" | jq 'if type == "array" then length else 0 end' 2>/dev/null || echo 0)

  if [ "$COUNT" -gt 0 ]; then
    HAS_COMMITS=true
    # Collect commit summaries: sha (short) + message first line
    COMMIT_LINES=$(echo "$RAW" | jq -r '.[] | "  - `\(.sha[0:7])` \(.commit.message | split("\n")[0])"' 2>/dev/null || echo "")
    {
      echo "### \`$REPO\` — $COUNT commit(s)"
      echo ""
      echo "$COMMIT_LINES"
      echo ""
    } >> "$REPORT_FILE"
    TOTAL=$((TOTAL + COUNT))
  fi
done <<< "$REPOS"

if [ "$HAS_COMMITS" = false ]; then
  echo "_No commits found in this window._" >> "$REPORT_FILE"
  echo "" >> "$REPORT_FILE"
fi

{
  echo "**Total: $TOTAL commit(s)**"
  echo ""
  echo "---"
  echo ""
} >> "$REPORT_FILE"

echo "Report written to $REPORT_FILE ($TOTAL total commits)"
