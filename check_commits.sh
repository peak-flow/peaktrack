#!/usr/bin/env bash
# Checks commits on peak-flow/peaktrack in the last 6 hours and appends to commit_log.md
set -euo pipefail

REPO_OWNER="peak-flow"
REPO="peaktrack"
LOG_FILE="$(dirname "$0")/commit_log.md"
SINCE=$(date -u -d '6 hours ago' +%Y-%m-%dT%H:%M:%SZ)
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)

if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "ERROR: GITHUB_TOKEN is not set" >&2
  exit 1
fi

# Fetch commits since 6 hours ago (up to 100)
RESPONSE=$(curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${REPO_OWNER}/${REPO}/commits?since=${SINCE}&per_page=100")

COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data) if isinstance(data, list) else 0)")

# Create log file with header if it doesn't exist
if [ ! -f "$LOG_FILE" ]; then
  cat > "$LOG_FILE" <<'HEADER'
# GitHub Commit Log — peak-flow/peaktrack

Automatically updated every 6 hours.

---

HEADER
fi

# Append new entry
cat >> "$LOG_FILE" <<ENTRY
## $(date -u +"%Y-%m-%d %H:%M UTC")

| Repository | Commits (last 6h) |
|---|---|
| ${REPO_OWNER}/${REPO} | ${COUNT} |

**Total commits:** ${COUNT}

> Period: \`${SINCE}\` → \`${NOW}\`

---

ENTRY

echo "Logged ${COUNT} commit(s) for ${REPO_OWNER}/${REPO} since ${SINCE}"
