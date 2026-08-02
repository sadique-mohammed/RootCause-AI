#!/bin/bash
# Reset script: 09-expired-tls-cert
# Removes the expired certificate and restores nginx config.

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Resetting incident 09-expired-tls-cert..."

# Remove expired cert and key
rm -f /etc/ssl/certs/expired.crt /etc/ssl/private/expired.key

# Restore original nginx default site config
if [ -f /etc/nginx/sites-available/default.bak ]; then
  cp /etc/nginx/sites-available/default.bak /etc/nginx/sites-available/default
  rm -f /etc/nginx/sites-available/default.bak
fi

systemctl restart nginx 2>/dev/null || true

echo "Incident 09 reset: Expired TLS cert removed, nginx config restored."
