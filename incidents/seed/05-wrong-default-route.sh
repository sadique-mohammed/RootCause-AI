#!/bin/bash
# Seed script: 05-wrong-default-route
# Replaces the default gateway with a bogus one.
# WARNING: This will break outbound connectivity (but SSH session stays alive).

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Seeding incident 05-wrong-default-route..."

# Save original default route info for reset
ORIGINAL_GW=$(ip route | grep "^default" | awk '{print $3}')
ORIGINAL_IF=$(ip route | grep "^default" | awk '{print $5}')

if [ -z "$ORIGINAL_GW" ] || [ -z "$ORIGINAL_IF" ]; then
  echo "Could not determine default route. Aborting."
  exit 1
fi

echo "$ORIGINAL_GW $ORIGINAL_IF" > /tmp/.original_route

# Replace default route with a bogus gateway
ip route del default
ip route add default via 10.255.255.254 dev "$ORIGINAL_IF"

echo "Incident 05 seeded: Default route changed to bogus gateway 10.255.255.254 (original: $ORIGINAL_GW via $ORIGINAL_IF)."
