#!/bin/bash
# Seed script: 07-high-cpu-runaway
# Spawns an infinite loop to consume 100% of one CPU core.

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Seeding incident 07-high-cpu-runaway..."

if [ -f /tmp/.rootcause_spin_pid ] && kill -0 "$(cat /tmp/.rootcause_spin_pid)" 2>/dev/null; then
  echo "Incident 07 already seeded: CPU spinner is running."
  exit 0
fi

# Spin a CPU core with an infinite bash loop
bash -c 'while true; do :; done' &
SPIN_PID=$!
echo "$SPIN_PID" > /tmp/.rootcause_spin_pid

echo "Incident 07 seeded: CPU spinner started (PID: $SPIN_PID)."
