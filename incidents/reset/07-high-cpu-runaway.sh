#!/bin/bash
# Reset script: 07-high-cpu-runaway
# Kills the CPU-spinning process.

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Resetting incident 07-high-cpu-runaway..."

if [ -f /tmp/.spin_pid ]; then
  SPIN_PID=$(cat /tmp/.spin_pid)
  kill "$SPIN_PID" 2>/dev/null || true
  rm -f /tmp/.spin_pid
fi

# Also kill any remaining bash infinite loops (belt and suspenders)
pkill -f "while true; do :; done" 2>/dev/null || true

echo "Incident 07 reset: CPU spinner killed."
