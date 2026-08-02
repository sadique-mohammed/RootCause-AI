#!/bin/bash
# Seed script: 02-disk-full
# Fills the root partition with a hidden dummy file.

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Seeding incident 02-disk-full..."

# Calculate available space on root partition (in KB), leave 50MB for safety
AVAIL_KB=$(df --output=avail / | tail -1 | tr -d ' ')
FILL_KB=$((AVAIL_KB - 51200))

if [ "$FILL_KB" -le 0 ]; then
  echo "Disk already nearly full, skipping fill."
  exit 0
fi

# Create a hidden filler file in /tmp
fallocate -l "${FILL_KB}K" /tmp/.disk_filler_hidden 2>/dev/null || \
  dd if=/dev/zero of=/tmp/.disk_filler_hidden bs=1K count="$FILL_KB" 2>/dev/null

echo "Incident 02 seeded: Disk full (hidden file in /tmp, ${FILL_KB}KB)."
