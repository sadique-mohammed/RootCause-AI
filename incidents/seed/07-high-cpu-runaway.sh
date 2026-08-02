#!/bin/bash
# Seed script: 07-high-cpu-runaway
# Spawns an infinite loop to consume 100% of one CPU core.

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Seeding incident 07-high-cpu-runaway..."

# Spin a CPU core with an infinite bash loop
bash -c 'while true; do :; done' &
SPIN_PID=$!
echo "$SPIN_PID" > /tmp/.spin_pid

echo "Incident 07 seeded: CPU spinner started (PID: $SPIN_PID)."
