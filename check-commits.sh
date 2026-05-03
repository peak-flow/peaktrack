#!/usr/bin/env bash
set -euo pipefail

REPO="peak-flow/peaktrack"
LOG_FILE="$(dirname "$0")/commit-log.md"
TOKEN_FILE="$HOME/.github_token"

# Load token
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
  TOKEN="$GITHUB_TOKEN"
elif [[ -f "$TOKEN_FILE" ]]; then
  TOKEN="$(cat "$TOKEN_FILE")"
else
  echo "ERROR: No GitHub token found. Set GITHUB_TOKEN or create $TOKEN_FILE" >&2
  exit 1
fi

SINCE=$(date -u -d '6 hours ago' '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null \
  || date -u -v-6H '+%Y-%m-%dT%H:%M:%SZ')  # macOS fallback

NOW=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

gh_api() {
  curl -sf \
    -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "$@"
}

# Get all branches (up to 100)
BRANCHES=$(gh_api "https://api.github.com/repos/$REPO/branches?per_page=100" \
  | jq -r '.[].name')

# Collect all commits across all branches, deduplicated by SHA
declare -A SEEN
ALL_COMMITS="[]"

while IFS= read -r branch; do
  ENCODED_BRANCH=$(python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1]))" "$branch")
  COMMITS=$(gh_api \
    "https://api.github.com/repos/$REPO/commits?sha=${ENCODED_BRANCH}&since=${SINCE}&per_page=100" \
    || echo "[]")

  # Merge unseen commits into ALL_COMMITS
  while IFS= read -r sha; do
    [[ -z "$sha" ]] && continue
    if [[ -z "${SEEN[$sha]:-}" ]]; then
      SEEN["$sha"]=1
      ENTRY=$(echo "$COMMITS" | jq --arg s "$sha" '.[] | select(.sha == $s)')
      ALL_COMMITS=$(echo "$ALL_COMMITS" | jq --argjson e "$ENTRY" '. + [$e]')
    fi
  done < <(echo "$COMMITS" | jq -r '.[].sha')

done <<< "$BRANCHES"

COMMIT_COUNT=$(echo "$ALL_COMMITS" | jq 'length')

# Build per-branch summary (branches that had at least one new commit)
BRANCH_SUMMARY=""
while IFS= read -r branch; do
  ENCODED_BRANCH=$(python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1]))" "$branch")
  COUNT=$(gh_api \
    "https://api.github.com/repos/$REPO/commits?sha=${ENCODED_BRANCH}&since=${SINCE}&per_page=1" \
    | jq 'length' || echo 0)
  if [[ "$COUNT" -gt 0 ]]; then
    BRANCH_SUMMARY+="- \`$branch\`: $COUNT commit(s)\n"
  fi
done <<< "$BRANCHES"

COMMIT_LINES=$(echo "$ALL_COMMITS" | jq -r \
  '.[] | "- [`\(.sha[0:7])`] **\(.commit.author.name)** — \(.commit.message | split("\n")[0]) (\(.commit.author.date))"')

# Append markdown entry
{
  echo ""
  echo "---"
  echo ""
  echo "## $(date -u '+%Y-%m-%d %H:%M UTC')"
  echo ""
  echo "**Repository:** \`$REPO\`  "
  echo "**Window:** \`$SINCE\` → \`$NOW\`  "
  echo "**Total unique commits:** $COMMIT_COUNT"
  echo ""
  if [[ "$COMMIT_COUNT" -gt 0 ]]; then
    echo "### Active Branches"
    echo ""
    echo -e "$BRANCH_SUMMARY"
    echo "### Commits"
    echo ""
    echo "$COMMIT_LINES"
  else
    echo "_No commits in this window._"
  fi
  echo ""
} >> "$LOG_FILE"

echo "Logged $COMMIT_COUNT unique commit(s) to $LOG_FILE"
