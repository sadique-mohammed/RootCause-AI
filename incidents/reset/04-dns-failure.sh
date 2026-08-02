#!/bin/bash
# Reset script: 04-dns-failure
# Restores outbound traffic on port 53 (DNS) using iptables.

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Resetting incident 04-dns-failure..."

while iptables -C OUTPUT -p udp --dport 53 -j DROP 2>/dev/null; do
  iptables -D OUTPUT -p udp --dport 53 -j DROP
done
while iptables -C OUTPUT -p tcp --dport 53 -j DROP 2>/dev/null; do
  iptables -D OUTPUT -p tcp --dport 53 -j DROP
done

echo "Incident reset successfully. Outbound DNS traffic is now permitted."
