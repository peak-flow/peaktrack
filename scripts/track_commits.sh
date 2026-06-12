#!/usr/bin/env bash
set -euo pipefail

# Track commits across all repos in the org over the last 6 hours.
# Requires: GITHUB_TOKEN env var, jq, curl
# Usage: ./track_commits.sh [org] [output_file]

ORG="${1:-peak-flow}"
OUTPUT="${2:-commit-tracker.md}"
HOURS=6

NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SINCE=$(date -u -d "${HOURS} hours ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
        || date -u -v"-${HOURS}H" +"%Y-%m-%dT%H:%M:%SZ")  # macOS fallback

api() {
  curl -fsSL \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "$@"
}

# Fetch all repos for the org (up to 100)
REPOS=$(api "https://api.github.com/orgs/${ORG}/repos?per_page=100&type=all" \
        | jq -r '.[].name')

if [[ -z "$REPOS" ]]; then
  echo "No repositories found for org: ${ORG}" >&2
  exit 1
fi

declare -A COUNTS
TOTAL=0
ACTIVE_REPOS=0

for REPO in $REPOS; do
  COUNT=$(api "https://api.github.com/repos/${ORG}/${REPO}/commits?since=${SINCE}&per_page=100" \
          | jq 'if type == "array" then length else 0 end' 2>/dev/null || echo 0)
  COUNTS["$REPO"]=$COUNT
  TOTAL=$((TOTAL + COUNT))
  if [[ $COUNT -gt 0 ]]; then
    ACTIVE_REPOS=$((ACTIVE_REPOS + 1))
  fi
done

# ── Build the new report block ──────────────────────────────────────────────
REPORT="## Report: $(date -u +"%Y-%m-%d %H:%M") UTC\n\n"
REPORT+="**Window:** last ${HOURS} hours (since \`${SINCE}\`)\n\n"

if [[ $TOTAL -eq 0 ]]; then
  REPORT+="No commits in the last ${HOURS} hours.\n"
else
  REPORT+="| Repository | Commits |\n"
  REPORT+="| --- | ---: |\n"
  for REPO in $(echo "$REPOS" | sort); do
    CNT=${COUNTS[$REPO]:-0}
    if [[ $CNT -gt 0 ]]; then
      REPORT+="| \`${ORG}/${REPO}\` | ${CNT} |\n"
    fi
  done
  REPORT+="\n**Total: ${TOTAL} commit(s) across ${ACTIVE_REPOS} repo(s)**\n"
fi
REPORT+="\n---\n"

# ── Write / prepend to the output file ──────────────────────────────────────
HEADER="# Commit Activity Tracker — ${ORG}\n\n_Auto-updated every ${HOURS} hours by GitHub Actions._\n\n---\n\n"

if [[ -f "$OUTPUT" ]]; then
  # Strip the existing header (first 5 lines) and prepend new report
  EXISTING=$(tail -n +6 "$OUTPUT")
  printf "%b%b\n%s" "$HEADER" "$REPORT" "$EXISTING" > "$OUTPUT"
else
  printf "%b%b" "$HEADER" "$REPORT" > "$OUTPUT"
fi

echo "Updated ${OUTPUT} — ${TOTAL} commit(s) found since ${SINCE}"
