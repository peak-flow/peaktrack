#!/usr/bin/env bash
# Queries GitHub API for commits in the last 6 hours and appends to a markdown log.

set -euo pipefail

LOG_FILE="/home/user/peaktrack/github-commit-log.md"
CONFIG_FILE="/home/user/peaktrack/scripts/.github-token"

# Load token from config file if env var not set
if [[ -z "${GITHUB_TOKEN:-}" && -f "$CONFIG_FILE" ]]; then
  GITHUB_TOKEN=$(cat "$CONFIG_FILE")
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "ERROR: GITHUB_TOKEN not set. Add it to $CONFIG_FILE or export it." >&2
  exit 1
fi

SINCE=$(date -u -d '6 hours ago' '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null \
  || date -u -v-6H '+%Y-%m-%dT%H:%M:%SZ')  # macOS fallback

NOW=$(date -u '+%Y-%m-%d %H:%M UTC')

gh_api() {
  curl -fsSL \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "$@"
}

# Create log file with header if it doesn't exist
if [[ ! -f "$LOG_FILE" ]]; then
  cat > "$LOG_FILE" <<'HEADER'
# GitHub Commit Activity Log

Auto-generated every 6 hours.

HEADER
fi

# Fetch repos accessible to the authenticated user (first 100)
repos_json=$(gh_api "https://api.github.com/user/repos?per_page=100&sort=pushed&direction=desc" 2>/dev/null || echo "[]")

total_commits=0
total_repos=0
table_rows=""

while IFS= read -r repo; do
  [[ -z "$repo" ]] && continue

  # Fetch commits since 6 hours ago for this repo
  commits_json=$(gh_api "https://api.github.com/repos/${repo}/commits?since=${SINCE}&per_page=100" 2>/dev/null || echo "[]")

  count=$(echo "$commits_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else 0)" 2>/dev/null || echo 0)

  if [[ "$count" -gt 0 ]]; then
    authors=$(echo "$commits_json" | python3 -c "
import sys, json
d = json.load(sys.stdin)
authors = sorted(set(
  (c.get('author') or {}).get('login') or (c.get('commit', {}).get('author') or {}).get('name', 'unknown')
  for c in d if isinstance(d, list)
))
print(', '.join('@' + a for a in authors))
" 2>/dev/null || echo "unknown")

    table_rows+="| \`${repo}\` | ${count} | ${authors} |"$'\n'
    total_commits=$((total_commits + count))
    total_repos=$((total_repos + 1))
  fi
done < <(echo "$repos_json" | python3 -c "
import sys, json
repos = json.load(sys.stdin)
for r in repos:
    print(r['full_name'])
" 2>/dev/null)

# Build the markdown entry
{
  echo "## ${NOW}"
  echo ""
  if [[ "$total_repos" -eq 0 ]]; then
    echo "_No commits in the last 6 hours._"
  else
    echo "| Repository | Commits | Authors |"
    echo "|------------|---------|---------|"
    printf "%s" "$table_rows"
    echo ""
    echo "**Total: ${total_commits} commit(s) across ${total_repos} repository/repositories**"
  fi
  echo ""
  echo "---"
  echo ""
} >> "$LOG_FILE"

echo "Done: ${total_commits} commits across ${total_repos} repos → $LOG_FILE"
