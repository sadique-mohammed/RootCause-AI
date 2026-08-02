#!/bin/bash
# Reset script: 03-memory-leak-oom
# Kills the memory-consuming Python process.

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Resetting incident 03-memory-leak-oom..."

if [ -f /tmp/.rootcause_leak_pid ]; then
  LEAK_PID=$(cat /tmp/.rootcause_leak_pid)
  kill "$LEAK_PID" 2>/dev/null || true
  rm -f /tmp/.rootcause_leak_pid
fi

# Also kill any remaining memory-hogging python processes from the seed
pkill -f "data.append" 2>/dev/null || true

echo "Incident 03 reset: Memory leak process killed."
