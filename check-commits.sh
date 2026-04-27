#!/usr/bin/env bash
# Checks peak-flow/peaktrack for commits in the last 6 hours and appends to commit-log.md
set -euo pipefail

GITHUB_TOKEN="${GITHUB_TOKEN:-}"
OWNER="peak-flow"
REPO="peaktrack"
LOG_FILE="$(dirname "$0")/commit-log.md"
SINCE=$(date -u -d '6 hours ago' '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null \
       || date -u -v-6H '+%Y-%m-%dT%H:%M:%SZ')  # Linux / macOS fallback
NOW=$(date -u '+%Y-%m-%d %H:%M UTC')

if [[ -z "$GITHUB_TOKEN" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set" >&2
  exit 1
fi

RESPONSE=$(curl -s \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${OWNER}/${REPO}/commits?since=${SINCE}&per_page=100")

COUNT=$(echo "$RESPONSE" | grep -c '"sha"' || true)

cat >> "$LOG_FILE" <<EOF

## ${NOW}

| Repo | Commits in last 6h |
|------|-------------------|
| ${OWNER}/${REPO} | ${COUNT} |

**Total:** ${COUNT} commits

---
EOF

echo "[${NOW}] ${OWNER}/${REPO}: ${COUNT} commit(s) in last 6h"
