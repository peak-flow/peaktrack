#!/usr/bin/env bash
# Checks GitHub repos for commits in the last 6 hours and appends to github-commit-log.md

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/github-commit-log.md"
HOURS=6

# Load token from ~/.github_token or GITHUB_TOKEN env var
if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  if [[ -f "$HOME/.github_token" ]]; then
    GITHUB_TOKEN="$(cat "$HOME/.github_token")"
  else
    echo "ERROR: No GitHub token found. Set GITHUB_TOKEN or create ~/.github_token" >&2
    exit 1
  fi
fi

# Repos to check — space-separated "owner/repo" pairs
REPOS="${GITHUB_REPOS:-peak-flow/peaktrack}"

NOW_ISO="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
SINCE_ISO="$(date -u -d "-${HOURS} hours" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
  || date -u -v-${HOURS}H +"%Y-%m-%dT%H:%M:%SZ")"  # macOS fallback

CHECK_TIME="$(date '+%Y-%m-%d %H:%M:%S %Z')"

# Build markdown entry
entry="## $CHECK_TIME\n\n"
entry+="**Period checked:** last ${HOURS} hours (since \`$SINCE_ISO\`)\n\n"

total_commits=0
any_activity=false

for repo in $REPOS; do
  response="$(curl -s \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$repo/commits?since=$SINCE_ISO&per_page=100")"

  # Check for API errors
  if echo "$response" | grep -q '"message"'; then
    msg="$(echo "$response" | grep -o '"message":"[^"]*"' | head -1)"
    entry+="### \`$repo\`\n\n- API error: $msg\n\n"
    continue
  fi

  count="$(echo "$response" | grep -c '"sha"' || true)"
  total_commits=$((total_commits + count))

  if [[ "$count" -gt 0 ]]; then
    any_activity=true
    entry+="### \`$repo\` — $count commit(s)\n\n"
    # Extract author + message for each commit (first 20)
    while IFS= read -r line; do
      entry+="$line\n"
    done < <(echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data[:20]:
    sha = c['sha'][:7]
    msg = c['commit']['message'].splitlines()[0][:80]
    author = c['commit']['author']['name']
    date = c['commit']['author']['date'][:10]
    print(f'- \`{sha}\` **{author}** ({date}): {msg}')
" 2>/dev/null || echo "  _(could not parse commit details)_")
    entry+="\n"
  else
    entry+="### \`$repo\` — no commits\n\n"
  fi
done

entry+="**Total commits across all repos:** $total_commits\n\n---\n"

# Ensure log file exists with a header
if [[ ! -f "$LOG_FILE" ]]; then
  printf '# GitHub Commit Log\n\nAuto-generated every %s hours.\n\n---\n\n' "$HOURS" > "$LOG_FILE"
fi

# Prepend new entry after the header line (insert after line 4)
tmp="$(mktemp)"
head -4 "$LOG_FILE" > "$tmp"
printf '\n%b\n' "$entry" >> "$tmp"
tail -n +5 "$LOG_FILE" >> "$tmp"
mv "$tmp" "$LOG_FILE"

echo "[$CHECK_TIME] Logged $total_commits commit(s) from $(echo $REPOS | wc -w) repo(s) to $LOG_FILE"
