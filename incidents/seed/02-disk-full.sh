#!/bin/bash
# Seed script: 02-disk-full
# Fills the root partition with a hidden dummy file.

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Seeding incident 02-disk-full..."

FILLER=/tmp/.rootcause_disk_filler_hidden
if [ -f "$FILLER" ]; then
  echo "Incident 02 already seeded: $FILLER exists."
  exit 0
fi

# Calculate available space on root partition (in KB), leave 50MB for safety
AVAIL_KB=$(df --output=avail / | tail -1 | tr -d ' ')
FILL_KB=$((AVAIL_KB - 51200))
MAX_FILL_KB=${ROOTCAUSE_DISK_FILL_KB:-524288}
if [ "$FILL_KB" -gt "$MAX_FILL_KB" ]; then
  FILL_KB=$MAX_FILL_KB
fi

if [ "$FILL_KB" -le 0 ]; then
  echo "Disk already nearly full, skipping fill."
  exit 0
fi

# Create a hidden filler file in /tmp
fallocate -l "${FILL_KB}K" "$FILLER" 2>/dev/null || \
  dd if=/dev/zero of="$FILLER" bs=1K count="$FILL_KB" status=none

echo "Incident 02 seeded: Disk full (hidden file in /tmp, ${FILL_KB}KB)."
