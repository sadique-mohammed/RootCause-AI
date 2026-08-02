#!/bin/bash
# 10-tcp-retransmissions.sh
# Incident Seed: Inject 30% packet loss via tc netem
#
# REQUIRES: sudo / root access on the target VM
# USAGE:    sudo bash incidents/seed/10-tcp-retransmissions.sh
# RESET:    sudo bash incidents/reset/10-tcp-retransmissions-reset.sh

set -euo pipefail

# Detect primary network interface (default route)
TARGET_IF=$(ip route | grep default | awk '{print $5}' | head -n 1)

if [ -z "$TARGET_IF" ]; then
    echo "ERROR: Could not detect default network interface."
    exit 1
fi

# Check if a qdisc rule already exists
if tc qdisc show dev "$TARGET_IF" | grep -q "netem"; then
    echo "WARNING: netem rule already exists on $TARGET_IF. Resetting first..."
    tc qdisc del dev "$TARGET_IF" root 2>/dev/null || true
fi

# Inject 30% packet loss
tc qdisc add dev "$TARGET_IF" root netem loss 30%

# Save interface name for the reset script
echo "$TARGET_IF" > /tmp/.tc_interface

echo "================================================"
echo "Incident 10 SEEDED"
echo "  Interface: $TARGET_IF"
echo "  Packet loss: 30% (tc netem)"
echo "  Reset with: sudo bash incidents/reset/10-tcp-retransmissions-reset.sh"
echo "================================================"
