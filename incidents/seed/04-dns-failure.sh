#!/bin/bash
# Seed script: 04-dns-failure
# Drops all outbound traffic on port 53 (DNS) using iptables.

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Seeding incident 04-dns-failure..."

iptables -A OUTPUT -p udp --dport 53 -j DROP
iptables -A OUTPUT -p tcp --dport 53 -j DROP

echo "Incident seeded successfully. Outbound DNS traffic is now blocked."
