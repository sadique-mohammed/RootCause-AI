#!/bin/bash
# Seed script: 03-memory-leak-oom
# Launches a Python process that continuously allocates memory.

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Seeding incident 03-memory-leak-oom..."

# Launch a memory-consuming Python process in the background
python3 -c "
import time
data = []
while True:
    data.append('x' * 10**6)  # ~1MB per iteration
    time.sleep(0.1)
" &
LEAK_PID=$!
echo "$LEAK_PID" > /tmp/.leak_pid

echo "Incident 03 seeded: Memory leak process started (PID: $LEAK_PID)."
