#!/usr/bin/env bash
set -euo pipefail

# Generates a markdown commit report for the last 6 hours across all accessible repos.
# Requires GITHUB_TOKEN or GITHUB_PAT env var with read:org + repo scopes.

TOKEN="${GITHUB_PAT:-${GITHUB_TOKEN:-}}"
if [[ -z "$TOKEN" ]]; then
  echo "ERROR: set GITHUB_PAT or GITHUB_TOKEN" >&2
  exit 1
fi

API="https://api.github.com"
SINCE=$(date -u -d "6 hours ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
     || date -u -v-6H +"%Y-%m-%dT%H:%M:%SZ")  # macOS fallback
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
REPORT_DIR="commit-reports"
REPORT_FILE="${REPORT_DIR}/$(date -u +"%Y-%m-%d").md"

mkdir -p "$REPORT_DIR"

auth_header() { echo "Authorization: Bearer $TOKEN"; }

# Fetch all repos (user + org) the token can see, paginated
fetch_repos() {
  local page=1
  while :; do
    local resp
    resp=$(curl -sf -H "$(auth_header)" -H "Accept: application/vnd.github+json" \
      "${API}/user/repos?per_page=100&page=${page}&sort=pushed&affiliation=owner,collaborator,organization_member")
    local count
    count=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d))" 2>/dev/null || echo 0)
    echo "$resp" | python3 -c "import sys,json; [print(r['full_name']) for r in json.load(sys.stdin)]" 2>/dev/null || true
    [[ "$count" -lt 100 ]] && break
    ((page++))
  done
}

# Fetch commit count for a repo since SINCE
fetch_commits() {
  local repo="$1"
  curl -sf -H "$(auth_header)" -H "Accept: application/vnd.github+json" \
    "${API}/repos/${repo}/commits?since=${SINCE}&per_page=100" 2>/dev/null \
  | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if isinstance(data, list):
        for c in data:
            sha = c.get('sha','')[:7]
            msg = (c.get('commit',{}).get('message','') or '').split('\n')[0][:72]
            author = c.get('commit',{}).get('author',{}).get('name','unknown')
            ts = c.get('commit',{}).get('author',{}).get('date','')
            print(f'{sha}|{author}|{ts}|{msg}')
except Exception:
    pass
" || true
}

echo "Fetching repos..."
mapfile -t REPOS < <(fetch_repos | sort -u)
echo "Found ${#REPOS[@]} repos. Checking commits since ${SINCE}..."

declare -A REPO_COMMITS
TOTAL=0

for repo in "${REPOS[@]}"; do
  commits=$(fetch_commits "$repo")
  count=$(echo "$commits" | grep -c '|' || true)
  if [[ $count -gt 0 ]]; then
    REPO_COMMITS["$repo"]="$commits"
    TOTAL=$((TOTAL + count))
    echo "  $repo: $count commit(s)"
  fi
done

# Build/update markdown report
{
  echo ""
  echo "---"
  echo ""
  echo "## $(date -u +"%Y-%m-%d %H:%M UTC") — ${TOTAL} commit(s) in last 6 hours"
  echo ""
  if [[ $TOTAL -eq 0 ]]; then
    echo "_No commits found in the last 6 hours._"
  else
    for repo in $(echo "${!REPO_COMMITS[@]}" | tr ' ' '\n' | sort); do
      count=$(echo "${REPO_COMMITS[$repo]}" | grep -c '|' || true)
      echo "### \`$repo\` — ${count} commit(s)"
      echo ""
      echo "| SHA | Author | Time (UTC) | Message |"
      echo "|-----|--------|-----------|---------|"
      while IFS='|' read -r sha author ts msg; do
        [[ -z "$sha" ]] && continue
        ts_short="${ts:0:16}"
        echo "| \`$sha\` | $author | $ts_short | $msg |"
      done <<< "${REPO_COMMITS[$repo]}"
      echo ""
    done
  fi
} >> "$REPORT_FILE"

# Write/refresh the header if file was just created
if ! grep -q "^# GitHub Commit Activity" "$REPORT_FILE" 2>/dev/null; then
  TMP=$(mktemp)
  {
    echo "# GitHub Commit Activity"
    echo ""
    echo "> Auto-generated every 6 hours. Each section is one run."
    cat "$REPORT_FILE"
  } > "$TMP"
  mv "$TMP" "$REPORT_FILE"
fi

echo ""
echo "Report written to $REPORT_FILE"
echo "REPORT_FILE=$REPORT_FILE" >> "${GITHUB_OUTPUT:-/dev/null}"
