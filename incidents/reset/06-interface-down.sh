#!/bin/bash
# Reset script: 06-interface-down
# Brings the downed interface back up and removes dummy if created.

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Resetting incident 06-interface-down..."

IF_MARKER=/tmp/.rootcause_down_interface
if [ ! -f "$IF_MARKER" ] && [ -f /tmp/.down_interface ]; then
  IF_MARKER=/tmp/.down_interface
fi

if [ -f "$IF_MARKER" ]; then
  TARGET_IF=$(cat "$IF_MARKER")
  ip link set "$TARGET_IF" up 2>/dev/null || true

  # Clean up dummy interface if we created one
  if [ "$TARGET_IF" = "dummy0" ]; then
    ip link del dummy0 2>/dev/null || true
  fi

  rm -f "$IF_MARKER" /tmp/.down_interface
  echo "Incident 06 reset: Interface $TARGET_IF brought back up."
else
  echo "No saved interface marker found. Network interfaces appear clean."
  exit 0
fi
