#!/bin/bash
# Seed script: 06-interface-down
# Brings down a secondary (non-SSH) network interface.
# WARNING: Requires a VM with at least two network interfaces.
# The script auto-detects the SSH interface and avoids touching it.

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Seeding incident 06-interface-down..."

# Identify the interface used for the current SSH connection
SSH_IF=$(ip route get 1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev") print $(i+1); exit}')

# Find a non-loopback, non-SSH interface to bring down
TARGET_IF=$(ip -br link show | grep -v "^lo " | grep -v "^${SSH_IF} " | awk '{print $1}' | head -1)

if [ -z "$TARGET_IF" ]; then
  echo "No secondary interface found. This incident requires a multi-NIC VM."
  echo "Falling back: creating a dummy interface to demonstrate the scenario."
  ip link add dummy0 type dummy
  ip addr add 10.99.99.1/24 dev dummy0
  ip link set dummy0 up
  sleep 1
  TARGET_IF="dummy0"
fi

echo "$TARGET_IF" > /tmp/.down_interface
ip link set "$TARGET_IF" down

echo "Incident 06 seeded: Interface $TARGET_IF brought down."
