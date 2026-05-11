#!/usr/bin/env bash
# Checks GitHub for commits in the last 6 hours and appends a report to the log file.

set -euo pipefail

REPO_OWNER="peak-flow"
REPOS=("peaktrack")
LOG_FILE="/home/user/peaktrack/github-commit-log.md"
TOKEN_FILE="${HOME}/.config/github-commit-checker/token"

# Load token from file if present; otherwise fall back to env var
if [[ -f "$TOKEN_FILE" ]]; then
  GITHUB_TOKEN="$(cat "$TOKEN_FILE")"
fi

SINCE=$(date -u -d "6 hours ago" +"%Y-%m-%dT%H:%M:%SZ")
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
NOW_HUMAN=$(date -u +"%Y-%m-%d %H:%M UTC")

auth_header=""
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
  auth_header="Authorization: Bearer ${GITHUB_TOKEN}"
fi

fetch_commits() {
  local owner="$1" repo="$2"
  local url="https://api.github.com/repos/${owner}/${repo}/commits?since=${SINCE}&per_page=100"
  local args=(-s -f -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28")
  [[ -n "$auth_header" ]] && args+=(-H "$auth_header")
  curl "${args[@]}" "$url"
}

# Create file with heading if it doesn't exist
if [[ ! -f "$LOG_FILE" ]]; then
  cat > "$LOG_FILE" <<'EOF'
# GitHub Commit Log

Auto-generated every 6 hours. Tracks commits across `peak-flow/peaktrack`.

---
EOF
fi

{
  echo ""
  echo "## $NOW_HUMAN"
  echo ""
  echo "| Repository | Commits in last 6h |"
  echo "|------------|-------------------|"

  total=0
  for repo in "${REPOS[@]}"; do
    response=$(fetch_commits "$REPO_OWNER" "$repo" 2>/dev/null || echo "[]")
    count=$(echo "$response" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data) if isinstance(data,list) else 0)" 2>/dev/null || echo "0")
    echo "| \`${REPO_OWNER}/${repo}\` | $count |"
    total=$((total + count))
  done

  echo ""
  echo "**Total commits:** $total  "
  echo "**Window:** \`${SINCE}\` → \`${NOW}\`"
  echo ""
  echo "---"
} >> "$LOG_FILE"

echo "Done. Appended report to $LOG_FILE (total commits: $total, window: $SINCE → $NOW)"
