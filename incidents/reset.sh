#!/usr/bin/env bash
# Reset one incident or all incidents on the configured target through the API.

set -euo pipefail

API_BASE_URL=${API_BASE_URL:-http://localhost:8000/api/v1}
INCIDENT_ID=${1:-all}

headers=(-H "Content-Type: application/json")
if [ -n "${INCIDENT_CONTROL_TOKEN:-}" ]; then
  headers+=(-H "Authorization: Bearer ${INCIDENT_CONTROL_TOKEN}")
fi

reset_one() {
  local incident_id=$1
  curl -fsS \
    "${headers[@]}" \
    -d "{\"incident_id\":\"${incident_id}\"}" \
    "${API_BASE_URL}/incidents/reset"
}

if [ "$INCIDENT_ID" = "all" ]; then
  for incident_id in 10 09 08 07 06 05 04 03 02 01; do
    echo "Resetting incident ${incident_id}..."
    reset_one "$incident_id" || true
    echo
  done
else
  reset_one "$INCIDENT_ID"
  echo
fi
