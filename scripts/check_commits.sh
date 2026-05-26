#!/usr/bin/env bash
# Fetches commits from peak-flow/peaktrack made in the last 6 hours
# and prepends a summary to commit-log.md.
#
# Requires: curl, jq
# Auth: set GITHUB_TOKEN env var, or store token in ~/.github_token

set -euo pipefail

OWNER="peak-flow"
REPO="peaktrack"
LOG_FILE="$(dirname "$0")/../commit-log.md"
HOURS=6

# Load token
if [ -z "${GITHUB_TOKEN:-}" ]; then
  if [ -f "$HOME/.github_token" ]; then
    GITHUB_TOKEN=$(cat "$HOME/.github_token")
  else
    echo "ERROR: No GITHUB_TOKEN set and ~/.github_token not found." >&2
    exit 1
  fi
fi

NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SINCE=$(date -u -d "${HOURS} hours ago" +%Y-%m-%dT%H:%M:%SZ)
WINDOW_START=$(date -u -d "${HOURS} hours ago" "+%Y-%m-%d %H:%M UTC")
WINDOW_END=$(date -u "+%Y-%m-%d %H:%M UTC")

api() {
  curl -fsSL \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "$@"
}

# Fetch all branches (paginated)
branches=()
page=1
while true; do
  resp=$(api "https://api.github.com/repos/${OWNER}/${REPO}/branches?per_page=100&page=${page}")
  names=$(echo "$resp" | jq -r '.[].name')
  [ -z "$names" ] && break
  while IFS= read -r name; do
    branches+=("$name")
  done <<< "$names"
  count=$(echo "$resp" | jq 'length')
  [ "$count" -lt 100 ] && break
  ((page++))
done

# Collect commits from each branch, deduplicate by SHA
declare -A seen_shas
rows=()

for branch in "${branches[@]}"; do
  encoded_branch=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$branch")
  commits=$(api "https://api.github.com/repos/${OWNER}/${REPO}/commits?sha=${encoded_branch}&since=${SINCE}&per_page=100" 2>/dev/null || echo "[]")

  while IFS= read -r line; do
    sha=$(echo "$line" | jq -r '.sha')
    [ -z "$sha" ] || [ "$sha" = "null" ] && continue
    [ "${seen_shas[$sha]+_}" ] && continue
    seen_shas[$sha]=1

    short_sha="${sha:0:7}"
    author=$(echo "$line" | jq -r '.commit.author.name // .author.login // "unknown"')
    message=$(echo "$line" | jq -r '.commit.message' | head -1 | cut -c1-72)
    rows+=("| \`${short_sha}\` | ${author} | \`${branch}\` | ${message} |")
  done < <(echo "$commits" | jq -c '.[]')
done

total=${#rows[@]}
timestamp=$(date -u "+%Y-%m-%d %H:%M UTC")

# Build the new entry
entry="## ${timestamp}\n\n"
entry+="**Repo:** ${OWNER}/${REPO}  \n"
entry+="**Window:** ${WINDOW_START} → ${WINDOW_END}  \n"
entry+="**Total commits:** ${total}\n\n"

if [ "$total" -eq 0 ]; then
  entry+="No commits were made in this 6-hour window.\n"
else
  entry+="| Commit | Author | Branch | Message |\n"
  entry+="|--------|--------|--------|---------|\n"
  for row in "${rows[@]}"; do
    entry+="${row}\n"
  done
fi

entry+="\n---\n"

# Prepend to log (after header block)
header=$(awk '/^---$/{found++; if(found==1){print; exit}} {print}' "$LOG_FILE")
rest=$(awk '/^---$/{found++} found>=1{if(NR>1)print}' "$LOG_FILE" | tail -n +2)

{
  echo "$header"
  echo ""
  printf '%b' "$entry"
  echo "$rest"
} > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"

echo "Done. ${total} commits found. Log updated: ${LOG_FILE}"
