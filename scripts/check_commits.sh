#!/usr/bin/env bash
# Fetches commits from the last 6 hours for peak-flow/peaktrack and appends to the activity log.
set -euo pipefail

GITHUB_TOKEN="${GITHUB_TOKEN:-}"
OWNER="peak-flow"
REPO="peaktrack"
LOG_FILE="/home/user/peaktrack/commit_activity_log.md"
HOURS=6

if [[ -z "$GITHUB_TOKEN" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set. Export it or add it to /etc/cron.d/peaktrack-commits." >&2
  exit 1
fi

now_epoch=$(date -u +%s)
since_epoch=$(( now_epoch - HOURS * 3600 ))
since_iso=$(date -u -d "@${since_epoch}" +"%Y-%m-%dT%H:%M:%SZ")
now_label=$(date -u +"%Y-%m-%d %H:%M UTC")

# Fetch commits since the window opened (paginate up to 3 pages / 300 commits)
all_commits="[]"
for page in 1 2 3; do
  page_data=$(curl -sf \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/${OWNER}/${REPO}/commits?since=${since_iso}&per_page=100&page=${page}" \
    || echo "[]")
  count=$(echo "$page_data" | jq 'length')
  all_commits=$(echo "$all_commits $page_data" | jq -s 'add')
  [[ "$count" -lt 100 ]] && break
done

total=$(echo "$all_commits" | jq 'length')

# Build per-author summary  (author login or name if no login)
by_author=$(echo "$all_commits" | jq -r '
  group_by(.author.login // .commit.author.name)[]
  | (.[0].author.login // .[0].commit.author.name) as $author
  | "  - \($author): \(length) commit(s)"
' | sort || echo "  - (no commits)")

# List individual commits (sha short + message first line)
commit_lines=$(echo "$all_commits" | jq -r '
  .[] | "  - [`\(.sha[0:7])`] \(.commit.message | split("\n")[0]) — \(.commit.author.name)"
' || echo "  - (none)")

# Append to log
{
  echo ""
  echo "## ${now_label}"
  echo ""
  echo "- **Repository:** \`${OWNER}/${REPO}\`"
  echo "- **Window:** last ${HOURS} hours (since \`${since_iso}\`)"
  echo "- **Total commits in last ${HOURS}h:** ${total}"
  echo ""
  if [[ "$total" -gt 0 ]]; then
    echo "### Commits by author"
    echo ""
    echo "$by_author"
    echo ""
    echo "### Commit list"
    echo ""
    echo "$commit_lines"
  else
    echo "_No commits in this window._"
  fi
  echo ""
  echo "---"
} >> "$LOG_FILE"

echo "[$(date -u +"%Y-%m-%d %H:%M UTC")] Logged ${total} commit(s) to ${LOG_FILE}"
