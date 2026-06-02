#!/usr/bin/env bash
# Checks GitHub for commits in the last 6 hours and appends a summary to commit-log.md.
# Requires: GITHUB_TOKEN env var, curl, jq
set -euo pipefail

REPO_OWNER="peak-flow"
REPOS=("peaktrack")
LOG_FILE="$(dirname "$0")/../commit-log.md"
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SINCE=$(date -u -d '6 hours ago' +%Y-%m-%dT%H:%M:%SZ)
DISPLAY_NOW=$(date -u '+%Y-%m-%d %H:%M UTC')

# Fetch commits for one repo since $SINCE
fetch_commits() {
  local owner="$1" repo="$2"
  curl -s \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${owner}/${repo}/commits?since=${SINCE}&per_page=100"
}

# Build the markdown entry
build_entry() {
  local total=0
  local table_rows=""
  local detail_sections=""

  for repo in "${REPOS[@]}"; do
    local json
    json=$(fetch_commits "$REPO_OWNER" "$repo")
    local count
    count=$(echo "$json" | jq 'length')
    total=$((total + count))

    table_rows+="| ${REPO_OWNER}/${repo} | ${count} |\n"

    if [ "$count" -gt 0 ]; then
      detail_sections+="\n### ${REPO_OWNER}/${repo}\n"
      local shown=0
      while IFS= read -r line; do
        detail_sections+="$line\n"
        shown=$((shown + 1))
      done < <(echo "$json" | jq -r '
        .[:20][] |
        "- `" + (.sha[0:7]) + "` **" + (.commit.author.name) + "** — " +
        (.commit.message | split("\n")[0]) +
        " *(" + (.commit.author.date[0:10]) + ")*"
      ')
      local remaining=$((count - shown))
      if [ "$remaining" -gt 0 ]; then
        detail_sections+="- …and ${remaining} more\n"
      fi
    fi
  done

  printf "## %s — %d commits in last 6 hours\n\n" "$DISPLAY_NOW" "$total"
  printf "| Repo | Commits |\n|------|---------|\n"
  printf "%b" "$table_rows"
  if [ -n "$detail_sections" ]; then
    printf "%b" "$detail_sections"
  else
    printf "\n*No commits in this window.*\n"
  fi
  printf "\n---\n"
}

build_entry >> "$LOG_FILE"
echo "Appended commit summary for $DISPLAY_NOW to $LOG_FILE"
