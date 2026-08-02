#!/bin/bash
# Seed script: 01-nginx-wont-start
# Introduces a syntax error in nginx.conf so the service fails to start.
# Requires: nginx installed on target VM (sudo apt install -y nginx)

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Seeding incident 01-nginx-wont-start..."

# Backup original config
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak

# Introduce syntax error: remove semicolon from worker_connections
sed -i 's/worker_connections [0-9]*;/worker_connections 768/' /etc/nginx/nginx.conf

# Stop nginx, then attempt restart (will fail due to syntax error)
systemctl stop nginx 2>/dev/null || true
systemctl start nginx 2>/dev/null || true

echo "Incident 01 seeded: Nginx won't start due to config syntax error."
