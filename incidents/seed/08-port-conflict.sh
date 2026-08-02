#!/bin/bash
# Seed script: 08-port-conflict
# Starts a dummy listener on port 80, then tries to start nginx (which fails to bind).
# Requires: nginx installed on target VM (sudo apt install -y nginx)

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Seeding incident 08-port-conflict..."

if [ -f /tmp/.rootcause_blocker_pid ] && kill -0 "$(cat /tmp/.rootcause_blocker_pid)" 2>/dev/null; then
  echo "Incident 08 already seeded: port blocker is running."
  exit 0
fi

# Stop nginx first to free port 80
systemctl stop nginx 2>/dev/null || true

# Start a dummy listener on port 80
python3 -c "
import socket, time
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', 80))
s.listen(1)
while True: time.sleep(60)
" &
BLOCKER_PID=$!
echo "$BLOCKER_PID" > /tmp/.rootcause_blocker_pid
sleep 1

# Try to start nginx (will fail because port 80 is occupied)
if systemctl start nginx 2>/dev/null; then
  echo "ERROR: nginx started successfully; port conflict was not seeded."
  kill "$BLOCKER_PID" 2>/dev/null || true
  rm -f /tmp/.rootcause_blocker_pid
  exit 1
fi

echo "Incident 08 seeded: Port 80 conflict (blocker PID: $BLOCKER_PID)."
