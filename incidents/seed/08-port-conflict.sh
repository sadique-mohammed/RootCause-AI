#!/bin/bash
# Seed script: 08-port-conflict
# Starts a dummy listener on port 80, then tries to start nginx (which fails to bind).
# Requires: nginx installed on target VM (sudo apt install -y nginx)

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Seeding incident 08-port-conflict..."

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
echo "$BLOCKER_PID" > /tmp/.blocker_pid
sleep 1

# Try to start nginx (will fail because port 80 is occupied)
systemctl start nginx 2>/dev/null || true

echo "Incident 08 seeded: Port 80 conflict (blocker PID: $BLOCKER_PID)."
