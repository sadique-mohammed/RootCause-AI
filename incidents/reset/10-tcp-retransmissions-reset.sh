#!/bin/bash
# 10-tcp-retransmissions-reset.sh
# Reset: Remove tc netem packet loss rule
#
# REQUIRES: sudo / root access on the target VM
# USAGE:    sudo bash incidents/reset/10-tcp-retransmissions-reset.sh

set -euo pipefail

# Read saved interface name
if [ -f /tmp/.tc_interface ]; then
    TARGET_IF=$(cat /tmp/.tc_interface)
else
    # Fallback: detect from default route
    TARGET_IF=$(ip route | grep default | awk '{print $5}' | head -n 1)
fi

if [ -z "$TARGET_IF" ]; then
    echo "ERROR: Could not determine network interface."
    exit 1
fi

# Remove the netem qdisc rule
if tc qdisc show dev "$TARGET_IF" | grep -q "netem"; then
    tc qdisc del dev "$TARGET_IF" root
    echo "Incident 10 RESET: Removed netem rule from $TARGET_IF"
else
    echo "No netem rule found on $TARGET_IF — already clean."
fi

# Clean up marker file
rm -f /tmp/.tc_interface
