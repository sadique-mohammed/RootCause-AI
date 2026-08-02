#!/bin/bash
# Reset script: 09-expired-tls-cert
# Removes the expired certificate and restores nginx config.

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Resetting incident 09-expired-tls-cert..."

# Remove expired cert and key
rm -f /etc/ssl/certs/rootcause-expired.crt /etc/ssl/private/rootcause-expired.key
rm -rf /tmp/rootcause-expired-cert

# Restore original nginx default site config
if [ -f /etc/nginx/sites-available/default.rootcause.bak ]; then
  cp /etc/nginx/sites-available/default.rootcause.bak /etc/nginx/sites-available/default
  rm -f /etc/nginx/sites-available/default.rootcause.bak
fi

nginx -t || true
systemctl restart nginx || true

echo "Incident 09 reset: Expired TLS cert removed, nginx config restored."
