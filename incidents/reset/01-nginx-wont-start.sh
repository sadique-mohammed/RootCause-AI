#!/bin/bash
# Reset script: 01-nginx-wont-start
# Restores original nginx.conf and restarts the service.

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Resetting incident 01-nginx-wont-start..."

# Restore backup config
if [ -f /etc/nginx/nginx.conf.rootcause.bak ]; then
  cp /etc/nginx/nginx.conf.rootcause.bak /etc/nginx/nginx.conf
  rm -f /etc/nginx/nginx.conf.rootcause.bak
fi

nginx -t || true
systemctl restart nginx || true

echo "Incident 01 reset: Nginx config restored and service restarted."
