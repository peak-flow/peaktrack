#!/usr/bin/env bash
# Checks each listed GitHub repo for commits in the past 6 hours and
# appends a summary block to commit_reports/commit_log.md.

set -euo pipefail

# ── CONFIG ────────────────────────────────────────────────────────────────────
# Add or remove repos in "owner/repo" format, one per line.
REPOS=(
  "peak-flow/peaktrack"
)

# GitHub personal access token (needs at least repo:read scope for private repos;
# public repos work without a token but rate-limits are tight without one).
# Set in your environment or replace the variable reference with the token string.
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

# How far back to look (seconds). 6 hours = 21600.
WINDOW_SECONDS=21600

# Where to write the markdown log.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORT_FILE="${SCRIPT_DIR}/../commit_reports/commit_log.md"
# ── END CONFIG ────────────────────────────────────────────────────────────────

now=$(date -u +%s)
since_ts=$(( now - WINDOW_SECONDS ))
since_iso=$(date -u -d "@${since_ts}" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
            || date -u -r "${since_ts}" +"%Y-%m-%dT%H:%M:%SZ")  # macOS fallback
report_ts=$(date -u +"%Y-%m-%d %H:%M UTC")

auth_header=""
if [[ -n "$GITHUB_TOKEN" ]]; then
  auth_header="Authorization: Bearer ${GITHUB_TOKEN}"
fi

# Accumulate results
total_commits=0
declare -A repo_counts

for repo in "${REPOS[@]}"; do
  repo_counts["$repo"]=0
  page=1
  count=0
  while true; do
    url="https://api.github.com/repos/${repo}/commits?since=${since_iso}&per_page=100&page=${page}"
    if [[ -n "$auth_header" ]]; then
      response=$(curl -sf -H "$auth_header" -H "Accept: application/vnd.github+json" "$url" || echo "[]")
    else
      response=$(curl -sf -H "Accept: application/vnd.github+json" "$url" || echo "[]")
    fi

    batch=$(echo "$response" | grep -o '"sha"' | wc -l | tr -d ' ') || batch=0
    count=$(( count + batch ))

    # Stop paging when the page is not full
    if [[ "$batch" -lt 100 ]]; then
      break
    fi
    page=$(( page + 1 ))
  done

  repo_counts["$repo"]=$count
  total_commits=$(( total_commits + count ))
done

# ── Write markdown block ───────────────────────────────────────────────────────
{
  echo ""
  echo "## ${report_ts}"
  echo ""
  echo "**Total commits in last 6 hours: ${total_commits}**"
  echo ""
  echo "| Repository | Commits |"
  echo "|------------|---------|"
  for repo in "${REPOS[@]}"; do
    echo "| \`${repo}\` | ${repo_counts[$repo]} |"
  done
  echo ""
  echo "---"
} >> "$REPORT_FILE"

echo "[$(date -u +"%H:%M UTC")] Logged ${total_commits} commit(s) across ${#REPOS[@]} repo(s) → ${REPORT_FILE}"
