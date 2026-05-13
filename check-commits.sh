#!/usr/bin/env bash
# Checks GitHub for commits in the last 6 hours and appends to github-commit-log.md
# Set GITHUB_TOKEN env var (or edit below) to authenticate and avoid rate limits.

set -euo pipefail

GITHUB_TOKEN="${GITHUB_TOKEN:-}"   # export GITHUB_TOKEN=ghp_... before running
LOG_FILE="$(dirname "$0")/github-commit-log.md"
HOURS=6

# Repos to check: "owner/repo" one per line
REPOS=(
  "peak-flow/peaktrack"
)

# ---- helpers ----------------------------------------------------------------

api_get() {
  local url="$1"
  local auth_header=""
  [[ -n "$GITHUB_TOKEN" ]] && auth_header="-H \"Authorization: Bearer $GITHUB_TOKEN\""
  curl -fsSL \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
    "$url"
}

# ---- main -------------------------------------------------------------------

NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SINCE=$(date -u -d "$HOURS hours ago" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
        || date -u -v-${HOURS}H +%Y-%m-%dT%H:%M:%SZ)  # macOS fallback

REPORT_TIME=$(date -u +"%Y-%m-%d %H:%M UTC")

# Ensure log file exists with a header
if [[ ! -f "$LOG_FILE" ]]; then
  cat > "$LOG_FILE" <<'HEADER'
# GitHub Commit Log

Auto-generated every 6 hours. Each entry covers the preceding 6-hour window.

---

HEADER
fi

# Build the report block
{
  echo "## [$REPORT_TIME] Commit Report"
  echo ""
  echo "_Window: ${SINCE} to ${NOW}_"
  echo ""

  TOTAL=0

  for REPO in "${REPOS[@]}"; do
    OWNER="${REPO%%/*}"
    NAME="${REPO##*/}"

    # Fetch up to 100 commits; add pages if you have very active repos
    RESPONSE=$(api_get \
      "https://api.github.com/repos/$OWNER/$NAME/commits?since=$SINCE&per_page=100" \
      2>/dev/null || echo "[]")

    COUNT=$(echo "$RESPONSE" | grep -c '"sha"' || true)

    echo "- **$REPO**: $COUNT commit(s)"

    if [[ "$COUNT" -gt 0 ]]; then
      # Print sha (short) + message + author for each commit
      echo "$RESPONSE" | python3 -c "
import sys, json
commits = json.load(sys.stdin)
for c in commits:
    sha   = c['sha'][:7]
    msg   = c['commit']['message'].splitlines()[0][:80]
    author = c['commit']['author']['name']
    print(f'  - \`{sha}\` {msg} ({author})')
" 2>/dev/null || true
    fi

    TOTAL=$((TOTAL + COUNT))
  done

  echo ""
  echo "_Total commits across all repos: **$TOTAL**_"
  echo ""
  echo "---"
  echo ""
} >> "$LOG_FILE"

echo "Done. $TOTAL commit(s) logged to $LOG_FILE"
