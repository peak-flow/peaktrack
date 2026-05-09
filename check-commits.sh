#!/usr/bin/env bash
set -euo pipefail

# Repositories to monitor (space-separated owner/repo pairs)
REPOS="peak-flow/peaktrack"

# GitHub Personal Access Token — required (unauthenticated requests are rate-limited).
# Set via environment or hardcode here:
#   export GITHUB_TOKEN=ghp_yourtoken
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

LOG_FILE="$(dirname "$0")/commit-log.md"
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SINCE=$(date -u -d "6 hours ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
        || date -u -v-6H +"%Y-%m-%dT%H:%M:%SZ")  # macOS fallback
DISPLAY_TIME=$(date -u +"%Y-%m-%d %H:%M UTC")

if [[ -z "$GITHUB_TOKEN" ]]; then
  echo "[ERROR] GITHUB_TOKEN is not set. Export it before running:" >&2
  echo "  export GITHUB_TOKEN=ghp_yourtoken" >&2
  exit 1
fi

CURL_AUTH=(-H "Authorization: Bearer $GITHUB_TOKEN" -H "X-GitHub-Api-Version: 2022-11-28")

total=0
entry="## $DISPLAY_TIME\n"

for REPO in $REPOS; do
  page=1
  repo_count=0
  commit_lines=""

  while true; do
    response=$(curl -s --fail-with-body \
      "${CURL_AUTH[@]}" \
      "https://api.github.com/repos/$REPO/commits?since=$SINCE&until=$NOW&per_page=100&page=$page" \
      2>&1) || { echo "[ERROR] Failed to fetch $REPO (page $page)" >&2; break; }

    count=$(echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if isinstance(data, list):
    print(len(data))
else:
    print('ERROR:' + data.get('message','unknown'))
    sys.exit(1)
" 2>&1) || { echo "[ERROR] $REPO: $count" >&2; break; }

    [[ "$count" -eq 0 ]] && break

    lines=$(echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data:
    sha = c['sha'][:7]
    author = (c.get('commit',{}).get('author',{}) or {}).get('name','unknown')
    msg = (c.get('commit',{}).get('message','') or '').split('\n')[0][:80]
    print(f'  - \`{sha}\` {author}: {msg}')
" 2>/dev/null)

    commit_lines+="$lines"$'\n'
    repo_count=$((repo_count + count))
    page=$((page + 1))
    [[ "$count" -lt 100 ]] && break
  done

  total=$((total + repo_count))
  entry+="- **$REPO**: $repo_count commit(s)\n"
  [[ -n "$commit_lines" ]] && entry+="$commit_lines"
done

entry+="- **Total**: $total commit(s) in last 6 hours\n"

# Create file with header if it doesn't exist
if [[ ! -f "$LOG_FILE" ]]; then
  printf "# GitHub Commit Log\n\nAuto-updated every 6 hours.\n\n" > "$LOG_FILE"
fi

# Prepend new entry after the header so newest is at top
tmp=$(mktemp)
head -n 4 "$LOG_FILE" > "$tmp"
printf "\n%b\n" "$entry" >> "$tmp"
tail -n +5 "$LOG_FILE" >> "$tmp"
mv "$tmp" "$LOG_FILE"

echo "Logged $total commit(s) at $DISPLAY_TIME"
