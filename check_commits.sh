#!/usr/bin/env bash
set -euo pipefail

# Load token from .env if present
ENV_FILE="$(dirname "$0")/.env"
if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

GITHUB_TOKEN="${GITHUB_TOKEN:-}"
REPO="peak-flow/peaktrack"
LOG_FILE="$(dirname "$0")/github_commit_log.md"
HOURS=6

if [ -z "$GITHUB_TOKEN" ]; then
  echo "ERROR: GITHUB_TOKEN is not set. Add it to /home/user/peaktrack/.env" >&2
  exit 1
fi

NOW_EPOCH=$(date +%s)
SINCE_EPOCH=$(( NOW_EPOCH - HOURS * 3600 ))
SINCE_ISO=$(date -u -d "@$SINCE_EPOCH" +"%Y-%m-%dT%H:%M:%SZ")
UNTIL_ISO=$(date -u -d "@$NOW_EPOCH"   +"%Y-%m-%dT%H:%M:%SZ")

fetch_commits() {
  local page=1
  local all="[]"
  while true; do
    local result
    result=$(curl -s -f \
      -H "Authorization: Bearer $GITHUB_TOKEN" \
      -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "https://api.github.com/repos/$REPO/commits?since=${SINCE_ISO}&until=${UNTIL_ISO}&per_page=100&page=${page}")
    local count
    count=$(echo "$result" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
    all=$(echo "$all $result" | python3 -c "
import sys, json
parts = sys.stdin.read().split(None, 1)
a = json.loads(parts[0])
b = json.loads(parts[1])
print(json.dumps(a + b))
" 2>/dev/null || echo "$all")
    if [ "$count" -lt 100 ]; then break; fi
    page=$(( page + 1 ))
  done
  echo "$all"
}

COMMITS_JSON=$(fetch_commits)

TOTAL=$(echo "$COMMITS_JSON" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")

# Build markdown entry
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M UTC")

ENTRY=$(python3 - <<PYEOF
import json, sys

commits = json.loads("""$COMMITS_JSON""")
total   = len(commits)
ts      = "$TIMESTAMP"
since   = "$SINCE_ISO"
until   = "$UNTIL_ISO"
repo    = "$REPO"

lines = []
lines.append(f"## {ts}")
lines.append(f"")
lines.append(f"**Repository:** \`{repo}\`  ")
lines.append(f"**Window:** {since} → {until}  ")
lines.append(f"**Total commits:** {total}")
lines.append(f"")

if total == 0:
    lines.append("_No commits in this window._")
else:
    lines.append("| SHA | Author | Message |")
    lines.append("|-----|--------|---------|")
    for c in commits:
        sha   = c.get("sha", "")[:7]
        author = (c.get("commit", {})
                   .get("author", {})
                   .get("name", "unknown"))
        msg   = (c.get("commit", {})
                  .get("message", "")
                  .split("\n")[0][:80])
        url   = c.get("html_url", "")
        lines.append(f"| [{sha}]({url}) | {author} | {msg} |")

lines.append("")
lines.append("---")
lines.append("")
print("\n".join(lines))
PYEOF
)

# Create file with header if it doesn't exist
if [ ! -f "$LOG_FILE" ]; then
  cat > "$LOG_FILE" <<'EOF'
# GitHub Commit Log — peak-flow/peaktrack

Checked every 6 hours. Each entry covers the preceding 6-hour window.

---

EOF
fi

echo "$ENTRY" >> "$LOG_FILE"
echo "[$TIMESTAMP] Logged $TOTAL commits to $LOG_FILE"
