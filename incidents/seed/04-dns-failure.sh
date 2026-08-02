#!/bin/bash
# Seed script: 04-dns-failure
# Drops all outbound traffic on port 53 (DNS) using iptables.

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Seeding incident 04-dns-failure..."

iptables -C OUTPUT -p udp --dport 53 -j DROP 2>/dev/null || iptables -A OUTPUT -p udp --dport 53 -j DROP
iptables -C OUTPUT -p tcp --dport 53 -j DROP 2>/dev/null || iptables -A OUTPUT -p tcp --dport 53 -j DROP

echo "Incident seeded successfully. Outbound DNS traffic is now blocked."
