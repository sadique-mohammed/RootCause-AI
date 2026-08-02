#!/bin/bash
# Reset script: 05-wrong-default-route
# Restores the original default gateway.

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Resetting incident 05-wrong-default-route..."

ROUTE_MARKER=/tmp/.rootcause_original_route
if [ ! -f "$ROUTE_MARKER" ] && [ -f /tmp/.original_route ]; then
  ROUTE_MARKER=/tmp/.original_route
fi

if [ -f "$ROUTE_MARKER" ]; then
  ORIGINAL_GW=$(awk '{print $1}' "$ROUTE_MARKER")
  ORIGINAL_IF=$(awk '{print $2}' "$ROUTE_MARKER")

  ip route del default 2>/dev/null || true
  ip route add default via "$ORIGINAL_GW" dev "$ORIGINAL_IF"
  rm -f "$ROUTE_MARKER" /tmp/.original_route

  echo "Incident 05 reset: Default route restored to $ORIGINAL_GW via $ORIGINAL_IF."
else
  echo "No backup route found. Manual intervention required."
  exit 1
fi
