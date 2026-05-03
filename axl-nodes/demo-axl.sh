#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root_dir="$script_dir/.."
out_file="$root_dir/docs/axl_demo_output.txt"

mkdir -p "$(dirname "$out_file")"

echo "Starting AXL nodes (background)..." | tee "$out_file"
"$script_dir/start-all.sh" >/dev/null 2>&1 || true
sleep 2

echo "\n=== Running mesh smoke test ===\n" | tee -a "$out_file"
bash "$script_dir/test-mesh.sh" >> "$out_file" 2>&1 || echo "(test-mesh.sh exited non-zero)" >> "$out_file"

echo "\n=== Node log tails ===\n" >> "$out_file"
for name in bull bear judge; do
  log_file="$script_dir/logs/$name.log"
  echo "--- $name log (tail 200 lines) ---" >> "$out_file"
  if [[ -f "$log_file" ]]; then
    tail -n 200 "$log_file" >> "$out_file" || true
  else
    echo "(no log file: $log_file)" >> "$out_file"
  fi
  echo "\n" >> "$out_file"
done

echo "\n=== /recv endpoints ===\n" >> "$out_file"
for port in 8001 8002 8003; do
  echo "== http://127.0.0.1:$port/recv ==" >> "$out_file"
  curl -s "http://127.0.0.1:$port/recv" >> "$out_file" || echo "(no response)" >> "$out_file"
  echo "\n" >> "$out_file"
done

echo "Stopping AXL nodes..." >> "$out_file"
"$script_dir/stop-all.sh" >> "$out_file" 2>&1 || true

echo "\nDemo complete. Output saved to: $out_file" | tee -a "$out_file"

echo "Done. To run: bash axl-nodes/demo-axl.sh" >&2
