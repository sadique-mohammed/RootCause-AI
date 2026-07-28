#!/bin/bash
# Reset script: 04-dns-failure
# Restores outbound traffic on port 53 (DNS) using iptables.

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Resetting incident 04-dns-failure..."

iptables -D OUTPUT -p udp --dport 53 -j DROP || true
iptables -D OUTPUT -p tcp --dport 53 -j DROP || true

echo "Incident reset successfully. Outbound DNS traffic is now permitted."
