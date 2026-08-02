#!/bin/bash
# Seed script: 03-memory-leak-oom
# Launches a bounded Python process that creates sustained memory pressure.

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Seeding incident 03-memory-leak-oom..."

if [ -f /tmp/.rootcause_leak_pid ] && kill -0 "$(cat /tmp/.rootcause_leak_pid)" 2>/dev/null; then
  echo "Incident 03 already seeded: memory pressure process is running."
  exit 0
fi

LEAK_MB=${ROOTCAUSE_MEM_LEAK_MB:-512}

# Launch a memory-consuming Python process in the background
python3 -c "
import time
data = []
target_mb = int('$LEAK_MB')
for _ in range(target_mb):
    data.append('x' * 10**6)
    time.sleep(0.1)
while True:
    time.sleep(60)
" &
LEAK_PID=$!
echo "$LEAK_PID" > /tmp/.rootcause_leak_pid

echo "Incident 03 seeded: Memory pressure process started (PID: $LEAK_PID, target: ${LEAK_MB}MB)."
