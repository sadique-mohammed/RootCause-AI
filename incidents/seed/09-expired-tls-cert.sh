#!/bin/bash
# Seed script: 09-expired-tls-cert
# Generates an already-expired self-signed TLS certificate and configures nginx to use it.
# Requires: nginx and openssl installed on target VM.

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Seeding incident 09-expired-tls-cert..."

WORK_DIR=/tmp/rootcause-expired-cert
mkdir -p "$WORK_DIR/demoCA/newcerts"
touch "$WORK_DIR/demoCA/index.txt"
echo 1000 > "$WORK_DIR/demoCA/serial"

openssl req -newkey rsa:2048 -nodes \
  -keyout /etc/ssl/private/rootcause-expired.key \
  -out "$WORK_DIR/request.csr" \
  -subj "/CN=localhost" >/dev/null 2>&1

cat > "$WORK_DIR/openssl.cnf" <<'EOF'
[ ca ]
default_ca = CA_default
[ CA_default ]
dir = /tmp/rootcause-expired-cert/demoCA
database = $dir/index.txt
new_certs_dir = $dir/newcerts
certificate = /etc/ssl/certs/rootcause-expired.crt
serial = $dir/serial
private_key = /etc/ssl/private/rootcause-expired.key
default_md = sha256
policy = policy_any
x509_extensions = usr_cert
copy_extensions = copy
[ policy_any ]
commonName = supplied
[ usr_cert ]
subjectAltName = DNS:localhost,IP:127.0.0.1
EOF

openssl ca -batch -selfsign \
  -config "$WORK_DIR/openssl.cnf" \
  -in "$WORK_DIR/request.csr" \
  -out /etc/ssl/certs/rootcause-expired.crt \
  -startdate 20200101000000Z \
  -enddate 20200102000000Z >/dev/null 2>&1

# Backup existing nginx default site config
if [ ! -f /etc/nginx/sites-available/default.rootcause.bak ]; then
  cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.rootcause.bak
fi

# Append an SSL server block pointing to the expired cert
if ! grep -q "RootCause AI Incident 09" /etc/nginx/sites-available/default; then
  cat >> /etc/nginx/sites-available/default <<'EOF'

# --- RootCause AI Incident 09: Expired TLS ---
server {
    listen 443 ssl;
    ssl_certificate /etc/ssl/certs/rootcause-expired.crt;
    ssl_certificate_key /etc/ssl/private/rootcause-expired.key;
    root /var/www/html;
}
EOF
fi

nginx -t
systemctl restart nginx

echo "Incident 09 seeded: Expired TLS certificate installed on nginx port 443."
