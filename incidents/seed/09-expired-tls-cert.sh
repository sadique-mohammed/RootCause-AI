#!/bin/bash
# Seed script: 09-expired-tls-cert
# Generates an already-expired self-signed TLS certificate and configures nginx to use it.
# Requires: nginx and openssl installed on target VM.

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Seeding incident 09-expired-tls-cert..."

# Generate an already-expired self-signed certificate (-1 days)
openssl req -x509 -newkey rsa:2048 \
  -keyout /etc/ssl/private/expired.key \
  -out /etc/ssl/certs/expired.crt \
  -days -1 -nodes \
  -subj "/CN=localhost" 2>/dev/null

# Backup existing nginx default site config
cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.bak 2>/dev/null || true

# Append an SSL server block pointing to the expired cert
cat >> /etc/nginx/sites-available/default <<'EOF'

# --- RootCause AI Incident 09: Expired TLS ---
server {
    listen 443 ssl;
    ssl_certificate /etc/ssl/certs/expired.crt;
    ssl_certificate_key /etc/ssl/private/expired.key;
    root /var/www/html;
}
EOF

systemctl restart nginx 2>/dev/null || true

echo "Incident 09 seeded: Expired TLS certificate installed on nginx port 443."
