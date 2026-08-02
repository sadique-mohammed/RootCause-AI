#!/bin/bash
# Seed script: 05-wrong-default-route
# Replaces the default gateway with a bogus one.
# WARNING: This will break outbound connectivity (but SSH session stays alive).

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

if [ "${ROOTCAUSE_ALLOW_ROUTE_BREAK:-false}" != "true" ]; then
  echo "ERROR: Incident 05 can make the VM unreachable. Set ROOTCAUSE_ALLOW_ROUTE_BREAK=true to run it in an out-of-band lab."
  exit 1
fi

echo "Seeding incident 05-wrong-default-route..."

if [ -f /tmp/.rootcause_original_route ]; then
  echo "Incident 05 already seeded; original route is already saved."
  exit 0
fi

# Save original default route info for reset
ORIGINAL_GW=$(ip route | awk '/^default/ {print $3; exit}')
ORIGINAL_IF=$(ip route | awk '/^default/ {print $5; exit}')

if [ -z "$ORIGINAL_GW" ] || [ -z "$ORIGINAL_IF" ]; then
  echo "Could not determine default route. Aborting."
  exit 1
fi

echo "$ORIGINAL_GW $ORIGINAL_IF" > /tmp/.rootcause_original_route

# Replace default route with a bogus gateway
ip route del default
ip route add default via 10.255.255.254 dev "$ORIGINAL_IF"

echo "Incident 05 seeded: Default route changed to bogus gateway 10.255.255.254 (original: $ORIGINAL_GW via $ORIGINAL_IF)."
