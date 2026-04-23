#!/usr/bin/env bash
# Queries GitHub API for commits in the last 6 hours across configured repos
# and appends a summary to commit_report.md.
# Requires: GITHUB_TOKEN env var, curl, jq

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPOS_CONFIG="$SCRIPT_DIR/repos.txt"
REPORT_FILE="$REPO_ROOT/commit_report.md"
HOURS=6

# Load .env if present (useful when run from cron where env is minimal)
if [[ -f "$REPO_ROOT/.env" ]]; then
  # shellcheck disable=SC1091
  set -a; source "$REPO_ROOT/.env"; set +a
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "ERROR: GITHUB_TOKEN environment variable is not set." >&2
  echo "       Set it in the environment or in $REPO_ROOT/.env" >&2
  exit 1
fi

if ! command -v jq &>/dev/null; then
  echo "ERROR: jq is required but not installed." >&2
  exit 1
fi

if [[ ! -f "$REPOS_CONFIG" ]]; then
  echo "ERROR: repos config not found at $REPOS_CONFIG" >&2
  exit 1
fi

SINCE="$(date -u -d "$HOURS hours ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
  || date -u -v-"${HOURS}"H +"%Y-%m-%dT%H:%M:%SZ")"

NOW="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

echo "## Commit Report: $NOW (last ${HOURS}h)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "| Repository | Commits | Authors |" >> "$REPORT_FILE"
echo "|------------|---------|---------|" >> "$REPORT_FILE"

TOTAL=0

while IFS= read -r repo || [[ -n "$repo" ]]; do
  # Skip blank lines and comments
  [[ -z "$repo" || "$repo" == \#* ]] && continue

  response=$(curl -sf \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/${repo}/commits?since=${SINCE}&per_page=100" \
    2>/dev/null) || {
    echo "| \`$repo\` | ERROR (API call failed) | — |" >> "$REPORT_FILE"
    continue
  }

  count=$(echo "$response" | jq 'length')
  authors=$(echo "$response" | jq -r '[.[].commit.author.name] | unique | join(", ")' 2>/dev/null || echo "—")

  echo "| \`$repo\` | $count | $authors |" >> "$REPORT_FILE"
  TOTAL=$((TOTAL + count))
done < "$REPOS_CONFIG"

echo "" >> "$REPORT_FILE"
echo "**Total commits across all repos: $TOTAL**" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "---" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "Done. Total commits: $TOTAL. Report saved to $REPORT_FILE"
