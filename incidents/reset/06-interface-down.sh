#!/bin/bash
# Reset script: 06-interface-down
# Brings the downed interface back up and removes dummy if created.

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Resetting incident 06-interface-down..."

if [ -f /tmp/.down_interface ]; then
  TARGET_IF=$(cat /tmp/.down_interface)
  ip link set "$TARGET_IF" up 2>/dev/null || true

  # Clean up dummy interface if we created one
  if [ "$TARGET_IF" = "dummy0" ]; then
    ip link del dummy0 2>/dev/null || true
  fi

  rm -f /tmp/.down_interface
  echo "Incident 06 reset: Interface $TARGET_IF brought back up."
else
  echo "No saved interface info found. Manual intervention required."
  exit 1
fi
