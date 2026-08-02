#!/usr/bin/env bash
# Cold-run benchmark harness for the incident catalog.

set -euo pipefail

API_BASE_URL=${API_BASE_URL:-http://localhost:8000/api/v1}
POLL_SECONDS=${POLL_SECONDS:-2}
MAX_POLLS=${MAX_POLLS:-60}

headers=(-H "Content-Type: application/json")
if [ -n "${INCIDENT_CONTROL_TOKEN:-}" ]; then
  headers+=(-H "Authorization: Bearer ${INCIDENT_CONTROL_TOKEN}")
fi

declare -A PROMPTS=(
  ["01"]="The website is down and nginx will not start."
  ["02"]="The server is reporting no disk space left on device."
  ["03"]="The VM is slow and memory usage is abnormally high."
  ["04"]="Applications cannot resolve domain names, but direct IP checks may still work."
  ["05"]="The VM cannot reach external networks after a route change."
  ["06"]="A service bound to a secondary interface is unreachable."
  ["07"]="The server CPU is pegged by an unknown process."
  ["08"]="Nginx cannot bind to port 80."
  ["09"]="HTTPS clients report that the TLS certificate is expired."
  ["10"]="TCP connections are slow and show retransmissions."
)

declare -A EXPECTED=(
  ["01"]="nginx|syntax|config"
  ["02"]="disk|space|filler|tmp"
  ["03"]="memory|process|pressure|leak"
  ["04"]="dns|resolver|port 53|nameserver"
  ["05"]="route|gateway|default"
  ["06"]="interface|down"
  ["07"]="cpu|process|spinner"
  ["08"]="port|80|bind|conflict"
  ["09"]="tls|certificate|expired"
  ["10"]="tcp|retransmission|packet loss|netem"
)

seed_incident() {
  local incident_id=$1
  curl -fsS \
    "${headers[@]}" \
    -d "{\"incident_id\":\"${incident_id}\"}" \
    "${API_BASE_URL}/incidents/seed" >/dev/null
}

reset_incident() {
  local incident_id=$1
  curl -fsS \
    "${headers[@]}" \
    -d "{\"incident_id\":\"${incident_id}\"}" \
    "${API_BASE_URL}/incidents/reset" >/dev/null
}

start_diagnosis() {
  local prompt=$1
  curl -fsS \
    -H "Content-Type: application/json" \
    -d "{\"incident_description\":\"${prompt}\"}" \
    "${API_BASE_URL}/diagnose"
}

poll_result() {
  local run_id=$1
  local attempt
  for attempt in $(seq 1 "$MAX_POLLS"); do
    result=$(curl -fsS "${API_BASE_URL}/diagnose/${run_id}")
    status=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("status", ""))' <<<"$result")
    if [ "$status" = "completed" ] || [ "$status" = "inconclusive" ] || [ "$status" = "failed" ]; then
      echo "$result"
      return 0
    fi
    sleep "$POLL_SECONDS"
  done
  echo "ERROR: diagnosis ${run_id} did not finish after ${MAX_POLLS} polls" >&2
  return 1
}

score_result() {
  local incident_id=$1
  local result_json=$2
  local pattern=${EXPECTED[$incident_id]}
  python3 -c '
import json
import re
import sys

pattern = sys.argv[1]
data = json.load(sys.stdin)
haystack = " ".join(
    str(data.get(key, ""))
    for key in ("root_cause", "root_cause_category", "suggested_fix", "summary")
).lower()
print("pass" if re.search(pattern, haystack) else "fail")
' "$pattern" <<<"$result_json"
}

passed=0
total=0

for incident_id in 01 02 03 04 05 06 07 08 09 10; do
  total=$((total + 1))
  echo "Running incident ${incident_id}..."
  if ! seed_incident "$incident_id"; then
    echo "Incident ${incident_id}: seed failed"
    reset_incident "$incident_id" || true
    continue
  fi

  response=$(start_diagnosis "${PROMPTS[$incident_id]}")
  run_id=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["run_id"])' <<<"$response")
  result=$(poll_result "$run_id")
  score=$(score_result "$incident_id" "$result")
  if [ "$score" = "pass" ]; then
    passed=$((passed + 1))
  fi
  echo "Incident ${incident_id}: ${score}"
  reset_incident "$incident_id" || true
done

echo "Benchmark result: ${passed}/${total}"

if [ "$passed" -lt 8 ]; then
  exit 1
fi
