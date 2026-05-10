#!/usr/bin/env bash
# Queries GitHub API for commits in the last 6 hours across configured repos
# and appends a summary to commit_log.md.
# Requires GITHUB_TOKEN env var (or set it directly below).

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
GITHUB_TOKEN="${GITHUB_TOKEN:-}"          # set here or export before running
REPOS=(
  "peak-flow/peaktrack"
  # add more repos as "owner/repo"
)
HOURS=6
OUTPUT_FILE="$(cd "$(dirname "$0")/.." && pwd)/commit_log.md"
# ─────────────────────────────────────────────────────────────────────────────

if [[ -z "$GITHUB_TOKEN" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set." >&2
  exit 1
fi

SINCE=$(date -u -d "${HOURS} hours ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
        || date -u -v-${HOURS}H +"%Y-%m-%dT%H:%M:%SZ")  # macOS fallback
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
RUN_AT=$(date -u +"%Y-%m-%d %H:%M UTC")

echo "Checking commits since ${SINCE} ..."

{
  echo ""
  echo "## ${RUN_AT}"
  echo ""
  echo "| Repository | Commits (last ${HOURS}h) |"
  echo "|------------|------------------------|"
} >> "$OUTPUT_FILE"

GRAND_TOTAL=0

for REPO in "${REPOS[@]}"; do
  OWNER="${REPO%%/*}"
  NAME="${REPO##*/}"
  PAGE=1
  TOTAL=0

  while true; do
    RESPONSE=$(curl -s -w "\n%{http_code}" \
      -H "Authorization: Bearer ${GITHUB_TOKEN}" \
      -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "https://api.github.com/repos/${OWNER}/${NAME}/commits?since=${SINCE}&until=${NOW}&per_page=100&page=${PAGE}")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n -1)

    if [[ "$HTTP_CODE" != "200" ]]; then
      echo "  WARN: ${REPO} returned HTTP ${HTTP_CODE}" >&2
      TOTAL="error"
      break
    fi

    COUNT=$(echo "$BODY" | grep -c '"sha"' || true)
    TOTAL=$((TOTAL + COUNT))

    # GitHub returns fewer than 100 items on the last page
    if [[ "$COUNT" -lt 100 ]]; then
      break
    fi
    PAGE=$((PAGE + 1))
  done

  echo "  ${REPO}: ${TOTAL} commit(s)"
  echo "| \`${REPO}\` | ${TOTAL} |" >> "$OUTPUT_FILE"

  if [[ "$TOTAL" != "error" ]]; then
    GRAND_TOTAL=$((GRAND_TOTAL + TOTAL))
  fi
done

echo "" >> "$OUTPUT_FILE"
echo "**Total: ${GRAND_TOTAL} commit(s) across ${#REPOS[@]} repo(s)**" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

echo "Done. Results appended to ${OUTPUT_FILE}"
