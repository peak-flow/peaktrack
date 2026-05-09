#!/usr/bin/env bash
set -euo pipefail

# Config
TOKEN_FILE="$HOME/.github_token"
LOG_FILE="/home/user/peaktrack/commit_log.md"
OWNER="peak-flow"
REPO="peaktrack"
HOURS=6

# Load token
if [[ ! -f "$TOKEN_FILE" ]]; then
  echo "ERROR: GitHub token file not found at $TOKEN_FILE" >&2
  echo "Create it with: echo 'ghp_yourtoken' > $TOKEN_FILE && chmod 600 $TOKEN_FILE" >&2
  exit 1
fi
TOKEN=$(cat "$TOKEN_FILE")

# Time window
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SINCE=$(date -u -d "${HOURS} hours ago" +%Y-%m-%dT%H:%M:%SZ)

# Fetch commits (handles pagination up to 300 commits)
PAGE=1
COMMITS_JSON="[]"
while true; do
  RESPONSE=$(curl -sf \
    -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/${OWNER}/${REPO}/commits?since=${SINCE}&until=${NOW}&per_page=100&page=${PAGE}" \
    || echo "[]")

  COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)

  if [[ "$COUNT" -eq 0 ]]; then
    break
  fi

  COMMITS_JSON=$(echo "$COMMITS_JSON $RESPONSE" | python3 -c "
import sys, json
parts = sys.stdin.read().split(None, 1)
a = json.loads(parts[0])
b = json.loads(parts[1])
print(json.dumps(a + b))
")
  PAGE=$((PAGE + 1))
  [[ "$COUNT" -lt 100 ]] && break
done

TOTAL=$(echo "$COMMITS_JSON" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")

# Build markdown entry
ENTRY=$(python3 - <<PYEOF
import json, sys

commits = json.loads("""$COMMITS_JSON""")
total = len(commits)
now = "$NOW"
since = "$SINCE"
owner = "$OWNER"
repo = "$REPO"

lines = []
lines.append(f"## {now} — Window: {since} → {now}")
lines.append("")
lines.append(f"**Repository:** {owner}/{repo}")
lines.append(f"**Commits in window:** {total}")
lines.append("")

if total == 0:
    lines.append("*(No commits found in this period.)*")
else:
    lines.append("| SHA | Author | Message |")
    lines.append("|-----|--------|---------|")
    for c in commits:
        sha = c["sha"][:7]
        author = (c.get("commit", {}).get("author") or {}).get("name", "unknown")
        msg = (c.get("commit", {}).get("message") or "").splitlines()[0][:80]
        lines.append(f"| \`{sha}\` | {author} | {msg} |")

lines.append("")
lines.append("---")
lines.append("")
print("\n".join(lines))
PYEOF
)

# Append to log
printf "\n%s" "$ENTRY" >> "$LOG_FILE"
echo "Logged $TOTAL commit(s) for ${OWNER}/${REPO} at $NOW"
