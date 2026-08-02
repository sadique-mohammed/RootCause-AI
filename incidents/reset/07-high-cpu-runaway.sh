#!/bin/bash
# Reset script: 07-high-cpu-runaway
# Kills the CPU-spinning process.

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Resetting incident 07-high-cpu-runaway..."

SPIN_MARKER=/tmp/.rootcause_spin_pid
if [ ! -f "$SPIN_MARKER" ] && [ -f /tmp/.spin_pid ]; then
  SPIN_MARKER=/tmp/.spin_pid
fi

if [ -f "$SPIN_MARKER" ]; then
  SPIN_PID=$(cat "$SPIN_MARKER")
  kill "$SPIN_PID" 2>/dev/null || true
  rm -f "$SPIN_MARKER" /tmp/.spin_pid
fi

# Also kill any remaining bash infinite loops (belt and suspenders)
pkill -f "while true; do :; done" 2>/dev/null || true

echo "Incident 07 reset: CPU spinner killed."
