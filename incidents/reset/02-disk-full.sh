#!/bin/bash
# Reset script: 02-disk-full
# Removes the hidden dummy file to free disk space.

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Resetting incident 02-disk-full..."

rm -f /tmp/.rootcause_disk_filler_hidden /tmp/.disk_filler_hidden

echo "Incident 02 reset: Hidden filler file removed."
