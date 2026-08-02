#!/bin/bash
# Reset script: 08-port-conflict
# Kills the dummy listener and restarts nginx.

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Resetting incident 08-port-conflict..."

if [ -f /tmp/.blocker_pid ]; then
  BLOCKER_PID=$(cat /tmp/.blocker_pid)
  kill "$BLOCKER_PID" 2>/dev/null || true
  rm -f /tmp/.blocker_pid
fi

# Also kill any remaining python socket listeners on port 80
pkill -f "s.bind" 2>/dev/null || true
sleep 1

systemctl restart nginx 2>/dev/null || true

echo "Incident 08 reset: Port blocker killed, nginx restarted."
