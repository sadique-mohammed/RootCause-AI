#!/bin/bash
# Seed script: 06-interface-down
# Brings down a secondary (non-SSH) network interface.
# WARNING: Requires a VM with at least two network interfaces.
# The script auto-detects the SSH interface and avoids touching it.

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Seeding incident 06-interface-down..."

if [ -f /tmp/.rootcause_down_interface ]; then
  echo "Incident 06 already seeded: interface marker exists."
  exit 0
fi

# Identify the interface used for the current SSH connection
SSH_IF=$(ip route get 1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev") print $(i+1); exit}')

# Find a non-loopback, non-SSH interface to bring down
TARGET_IF=$(ip -br link show | awk -v ssh_if="$SSH_IF" '$1 != "lo" && $1 != ssh_if {print $1; exit}')

if [ -z "$TARGET_IF" ]; then
  echo "No secondary interface found. This incident requires a multi-NIC VM."
  echo "Falling back: creating a dummy interface to demonstrate the scenario."
  ip link show dummy0 >/dev/null 2>&1 || ip link add dummy0 type dummy
  if ! ip addr show dev dummy0 | grep -q "10.99.99.1/24"; then
    ip addr add 10.99.99.1/24 dev dummy0
  fi
  ip link set dummy0 up
  sleep 1
  TARGET_IF="dummy0"
fi

echo "$TARGET_IF" > /tmp/.rootcause_down_interface
ip link set "$TARGET_IF" down

echo "Incident 06 seeded: Interface $TARGET_IF brought down."
