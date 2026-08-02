#!/bin/bash
# Reset script: 01-nginx-wont-start
# Restores original nginx.conf and restarts the service.

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Resetting incident 01-nginx-wont-start..."

# Restore backup config
if [ -f /etc/nginx/nginx.conf.bak ]; then
  cp /etc/nginx/nginx.conf.bak /etc/nginx/nginx.conf
  rm -f /etc/nginx/nginx.conf.bak
fi

systemctl restart nginx 2>/dev/null || true

echo "Incident 01 reset: Nginx config restored and service restarted."
