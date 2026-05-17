#!/usr/bin/env bash
set -euo pipefail

OWNER="peak-flow"
REPO="peaktrack"
LOG_FILE="/home/user/peaktrack/commit_log.md"
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SINCE=$(date -u -d "6 hours ago" +"%Y-%m-%dT%H:%M:%SZ")
NOW_HUMAN=$(date -u +"%Y-%m-%d %H:%M UTC")

if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "ERROR: GITHUB_TOKEN is not set" >&2
  exit 1
fi

# Fetch up to 3 pages of repo events (300 total), enough to cover 6 hours of activity
fetch_events() {
  local page=$1
  curl -sf \
    -H "Authorization: token ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/${OWNER}/${REPO}/events?per_page=100&page=${page}"
}

all_events="[]"
for page in 1 2 3; do
  page_data=$(fetch_events "$page" || echo "[]")
  count=$(echo "$page_data" | jq 'length')
  all_events=$(echo "$all_events $page_data" | jq -s 'add')
  # Stop early if page returned fewer than 100 events
  [ "$count" -lt 100 ] && break
done

# Filter PushEvents within the last 6 hours and extract branch + commit info
branch_summary=$(echo "$all_events" | jq -r --arg since "$SINCE" '
  [ .[]
    | select(.type == "PushEvent")
    | select(.created_at >= $since)
    | {
        branch: (.payload.ref | ltrimstr("refs/heads/")),
        commits: (.payload.commits | length),
        authors: [.payload.commits[].author.name] | unique | join(", ")
      }
  ]
  | group_by(.branch)
  | map({
      branch: .[0].branch,
      commits: map(.commits) | add,
      authors: (map(.authors) | join(", ") | split(", ") | unique | join(", "))
    })
  | .[]
  | "| \(.branch) | \(.commits) | \(.authors) |"
')

total_commits=$(echo "$all_events" | jq --arg since "$SINCE" '
  [ .[]
    | select(.type == "PushEvent")
    | select(.created_at >= $since)
    | .payload.commits | length
  ] | add // 0
')

# Build the markdown entry
if [ -z "$branch_summary" ]; then
  table_rows="| _(no commits)_ | 0 | — |"
else
  table_rows="$branch_summary"
fi

entry=$(cat <<ENTRY

---

## Check at ${NOW_HUMAN}

**Period:** ${SINCE} → ${NOW}
**Total commits:** ${total_commits}
**Repo:** ${OWNER}/${REPO}

| Branch | Commits | Authors |
|--------|---------|---------|
${table_rows}
ENTRY
)

# Create file with header if it doesn't exist
if [ ! -f "$LOG_FILE" ]; then
  cat > "$LOG_FILE" <<HEADER
# GitHub Commit Log — ${OWNER}/${REPO}

Automatically updated every 6 hours.
HEADER
fi

echo "$entry" >> "$LOG_FILE"
echo "Logged ${total_commits} commit(s) at ${NOW_HUMAN}"
