#!/usr/bin/env bash
# check_commits.sh — Fetch commits to peak-flow/peaktrack in the last 6 hours
# and append a summary entry to commit_log.md.
#
# Requirements:
#   - GITHUB_TOKEN env var must be set (a personal access token with repo read scope)
#   - curl and jq must be installed
#
# Cron schedule: 0 */6 * * *  (every 6 hours at :00)

set -euo pipefail

OWNER="peak-flow"
REPO="peaktrack"
LOG_FILE="$(dirname "$0")/commit_log.md"
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SIX_HOURS_AGO=$(date -u -d "6 hours ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
  || date -u -v -6H +"%Y-%m-%dT%H:%M:%SZ")  # Linux / macOS fallback

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "[$(date -u)] ERROR: GITHUB_TOKEN is not set. Skipping check." >> "$LOG_FILE"
  exit 1
fi

API="https://api.github.com"
AUTH_HEADER="Authorization: Bearer $GITHUB_TOKEN"

# ── Fetch all branches ──────────────────────────────────────────────────────
branches=$(curl -sf -H "$AUTH_HEADER" \
  "$API/repos/$OWNER/$REPO/branches?per_page=100" | jq -r '.[].name')

declare -A seen_shas
all_commits_md=""
total=0

for branch in $branches; do
  page=1
  while true; do
    response=$(curl -sf -H "$AUTH_HEADER" \
      "$API/repos/$OWNER/$REPO/commits?sha=$branch&since=$SIX_HOURS_AGO&per_page=100&page=$page" \
      || echo "[]")

    count=$(echo "$response" | jq 'length')
    if [[ "$count" -eq 0 ]]; then break; fi

    while IFS= read -r row; do
      sha=$(echo "$row"    | jq -r '.sha')
      msg=$(echo "$row"    | jq -r '.commit.message | split("\n")[0]')
      author=$(echo "$row" | jq -r '.commit.author.name')
      ts=$(echo "$row"     | jq -r '.commit.author.date')

      if [[ -z "${seen_shas[$sha]:-}" ]]; then
        seen_shas[$sha]=1
        total=$((total + 1))
        all_commits_md+="- \`${sha:0:7}\` **$branch** — $msg *(by $author at $ts)*\n"
      fi
    done < <(echo "$response" | jq -c '.[]')

    page=$((page + 1))
    [[ "$count" -lt 100 ]] && break
  done
done

# ── Write entry to log ──────────────────────────────────────────────────────
{
  echo ""
  echo "## $NOW"
  echo ""
  echo "**Window:** $SIX_HOURS_AGO → $NOW  "
  echo "**Repo:** $OWNER/$REPO  "
  echo "**Commits in window:** $total"
  echo ""
  if [[ $total -eq 0 ]]; then
    echo "> No new commits in this 6-hour window."
  else
    echo -e "$all_commits_md"
  fi
  echo ""
  echo "---"
} >> "$LOG_FILE"

echo "[$(date -u)] Logged $total commit(s) to $LOG_FILE"
