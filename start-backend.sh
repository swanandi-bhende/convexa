#!/usr/bin/env bash
set -euo pipefail

# Start the AXL nodes in the background
echo "Starting AXL nodes..."
bash axl-nodes/start-all.sh

# Wait a couple of seconds for the nodes to initialize and discover each other
sleep 3

# Start the Python orchestrator
echo "Starting Convexa Orchestrator..."
# Render will pass environment variables automatically
python3 orchestrator.py --token ETH --duration 5rounds
