#!/usr/bin/env bash
# Checks GitHub repos for commits in the last 6 hours and appends a summary to commit-log.md

set -euo pipefail

TOKEN="${GITHUB_TOKEN:-}"
OUTPUT="/home/user/peaktrack/commit-log.md"
HOURS=6

# Repos to track (format: "owner/repo")
REPOS=(
  "peak-flow/peaktrack"
)

if [[ -z "$TOKEN" ]]; then
  echo "ERROR: GITHUB_TOKEN environment variable is not set." >&2
  exit 1
fi

since=$(date -u -d "${HOURS} hours ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
  || date -u -v-${HOURS}H +"%Y-%m-%dT%H:%M:%SZ")  # macOS fallback

timestamp=$(date -u +"%Y-%m-%d %H:%M UTC")

# Create file with header if it doesn't exist
if [[ ! -f "$OUTPUT" ]]; then
  cat > "$OUTPUT" <<'EOF'
# GitHub Commit Log

Auto-generated every 6 hours. Each entry covers the preceding 6-hour window.

---

EOF
fi

entry="## ${timestamp}\n\n"
total_across_repos=0
has_activity=false

for repo in "${REPOS[@]}"; do
  owner="${repo%%/*}"
  name="${repo##*/}"

  # Fetch branches
  branches=$(curl -sf \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${repo}/branches?per_page=100" \
    | grep -o '"name":"[^"]*"' | sed 's/"name":"//;s/"//' || true)

  if [[ -z "$branches" ]]; then
    entry+="### \`${repo}\`\n\nNo branches found or API error.\n\n"
    continue
  fi

  repo_total=0
  repo_details=""

  while IFS= read -r branch; do
    [[ -z "$branch" ]] && continue

    commits_json=$(curl -sf \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "Accept: application/vnd.github+json" \
      "https://api.github.com/repos/${repo}/commits?sha=${branch}&since=${since}&per_page=100" \
      || echo "[]")

    count=$(echo "$commits_json" | grep -o '"sha"' | wc -l | tr -d ' ')

    if [[ "$count" -gt 0 ]]; then
      has_activity=true
      repo_total=$((repo_total + count))
      repo_details+="- **\`${branch}\`** — ${count} commit(s)\n"

      # Extract commit messages (first 100 chars each)
      messages=$(echo "$commits_json" \
        | grep -o '"message":"[^"]*"' \
        | sed 's/"message":"//;s/"$//' \
        | head -20 \
        | while IFS= read -r msg; do
            msg="${msg:0:100}"
            echo "  - \`${msg}\`"
          done)
      repo_details+="${messages}\n"
    fi
  done <<< "$branches"

  total_across_repos=$((total_across_repos + repo_total))

  if [[ "$repo_total" -gt 0 ]]; then
    entry+="### \`${repo}\` — ${repo_total} commit(s)\n\n${repo_details}\n"
  else
    entry+="### \`${repo}\` — no new commits\n\n"
  fi
done

entry+="**Total commits across all repos:** ${total_across_repos}\n\n---\n\n"

# Prepend entry after the header (after the first ---)
tmp=$(mktemp)
awk -v entry="$entry" '
  /^---$/ && !done {
    print
    printf "\n%s", entry
    done=1
    next
  }
  { print }
' "$OUTPUT" > "$tmp" && mv "$tmp" "$OUTPUT"

echo "Done. ${total_across_repos} commit(s) found. Log updated: ${OUTPUT}"
