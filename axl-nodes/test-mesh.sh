#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bear_peer="$(curl -s http://127.0.0.1:8002/topology | python3 -c 'import json,sys; print(json.load(sys.stdin)["our_public_key"])')"
judge_peer="$(curl -s http://127.0.0.1:8003/topology | python3 -c 'import json,sys; print(json.load(sys.stdin)["our_public_key"])')"

curl -sS -X POST "http://127.0.0.1:8001/send" \
  -H "X-Destination-Peer-Id: $judge_peer" \
  --data-binary '{"type":"test","content":"hello from bull"}' >/dev/null

sleep 1
judge_recv="$(curl -s http://127.0.0.1:8003/recv || true)"
if [[ "$judge_recv" != *"hello from bull"* ]]; then
  echo "Judge did not receive bull test message" >&2
  exit 1
fi

curl -sS -X POST "http://127.0.0.1:8001/send" \
  -H "X-Destination-Peer-Id: $bear_peer" \
  --data-binary '{"type":"test","content":"hello from bull"}' >/dev/null

sleep 1
bear_recv="$(curl -s http://127.0.0.1:8002/recv || true)"
if [[ "$bear_recv" != *"hello from bull"* ]]; then
  echo "Bear did not receive bull test message" >&2
  exit 1
fi

judge_check="$(curl -s http://127.0.0.1:8003/recv || true)"
if [[ "$judge_check" == *"hello from bull"* ]]; then
  echo "Judge received a message intended for Bear" >&2
  exit 1
fi

echo "AXL mesh smoke test passed"