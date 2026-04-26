#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
log_dir="$script_dir/logs"
binary="$script_dir/axl"

mkdir -p "$log_dir"

start_node() {
  local name="$1"
  local node_dir="$script_dir/$name"
  local log_file="$log_dir/$name.log"

  if [[ ! -f "$node_dir/data/private.pem" ]]; then
    openssl genpkey -algorithm ed25519 -out "$node_dir/data/private.pem"
  fi

  pushd "$node_dir" >/dev/null
  "$binary" -config node-config.json > "$log_file" 2>&1 &
  echo $! > "$log_dir/$name.pid"
  popd >/dev/null
}

start_node bull
start_node bear
start_node judge

echo "Bull PID: $(cat "$log_dir/bull.pid")"
echo "Bear PID: $(cat "$log_dir/bear.pid")"
echo "Judge PID: $(cat "$log_dir/judge.pid")"