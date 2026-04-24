#!/bin/bash
# Queries GitHub for commits across configured repos in the last 6 hours,
# then appends a summary to commit_report.md.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_FILE="$SCRIPT_DIR/commit_report.md"

# Repos to monitor — space-separated "owner/repo" entries
REPOS=(
  "peak-flow/peaktrack"
)

# Token: set GITHUB_TOKEN in your environment or pass it here
TOKEN="${GITHUB_TOKEN:-}"
if [[ -z "$TOKEN" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set." >&2
  exit 1
fi

SINCE=$(date -u -d '6 hours ago' '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null \
        || date -u -v-6H '+%Y-%m-%dT%H:%M:%SZ')
NOW=$(date -u '+%Y-%m-%d %H:%M:%S UTC')

# Ensure the report file exists with a header on first run
if [[ ! -f "$OUTPUT_FILE" ]]; then
  printf '# GitHub Commit Activity Log\n\nGenerated every 6 hours.\n\n---\n\n' > "$OUTPUT_FILE"
fi

{
  echo "## $NOW"
  echo ""
  echo "**Window:** last 6 hours (since \`$SINCE\`)"
  echo ""

  TOTAL=0

  for REPO in "${REPOS[@]}"; do
    RESPONSE=$(curl -sf \
      -H "Authorization: token $TOKEN" \
      -H "Accept: application/vnd.github.v3+json" \
      "https://api.github.com/repos/$REPO/commits?since=$SINCE&per_page=100" \
      || echo "[]")

    COUNT=$(printf '%s' "$RESPONSE" | python3 -c \
      "import json,sys; data=json.load(sys.stdin); print(len(data) if isinstance(data,list) else 0)")

    TOTAL=$((TOTAL + COUNT))

    echo "### \`$REPO\` — $COUNT commit(s)"
    echo ""

    if [[ "$COUNT" -gt 0 ]]; then
      printf '%s' "$RESPONSE" | python3 - <<'PYEOF'
import json, sys
data = json.load(sys.stdin)
for c in data:
    sha  = c["sha"][:7]
    msg  = c["commit"]["message"].split("\n")[0][:80]
    auth = c["commit"]["author"]["name"]
    date = c["commit"]["author"]["date"]
    print(f"- `{sha}` {msg}  _(_{auth}_, {date})_")
PYEOF
      echo ""
    fi
  done

  echo "**Total commits across all repos:** $TOTAL"
  echo ""
  echo "---"
  echo ""
} >> "$OUTPUT_FILE"

echo "[$NOW] Report updated — $TOTAL commit(s) across ${#REPOS[@]} repo(s)."
