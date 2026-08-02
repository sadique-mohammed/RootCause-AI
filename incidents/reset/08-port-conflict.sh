#!/bin/bash
# Reset script: 08-port-conflict
# Kills the dummy listener and restarts nginx.

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Resetting incident 08-port-conflict..."

BLOCKER_MARKER=/tmp/.rootcause_blocker_pid
if [ ! -f "$BLOCKER_MARKER" ] && [ -f /tmp/.blocker_pid ]; then
  BLOCKER_MARKER=/tmp/.blocker_pid
fi

if [ -f "$BLOCKER_MARKER" ]; then
  BLOCKER_PID=$(cat "$BLOCKER_MARKER")
  kill "$BLOCKER_PID" 2>/dev/null || true
  rm -f "$BLOCKER_MARKER" /tmp/.blocker_pid
fi

# Also kill any remaining python socket listeners on port 80
pkill -f "s.bind" 2>/dev/null || true
sleep 1

systemctl restart nginx || true

echo "Incident 08 reset: Port blocker killed, nginx restarted."
