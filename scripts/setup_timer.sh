#!/usr/bin/env bash
# Run this once to register and start the 6-hour GitHub commit-check timer.
# Requires a systemd user session (standard Linux desktop/server, not Docker).

set -euo pipefail

echo "Reloading systemd user daemon..."
systemctl --user daemon-reload

echo "Enabling and starting timer..."
systemctl --user enable --now github-commit-check.timer

echo ""
echo "Timer status:"
systemctl --user list-timers github-commit-check.timer

echo ""
echo "Done. The script will run at 00:00, 06:00, 12:00, and 18:00 UTC each day."
echo "Logs: /home/user/peaktrack/commit_reports/cron.log"
echo "Report: /home/user/peaktrack/commit_reports/commit_log.md"
