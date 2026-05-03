#!/usr/bin/env bash
set -euo pipefail

# Start the Next.js frontend in the background
echo "Starting Next.js frontend..."
cd frontend
npm start &
cd ..

# Start the Python orchestrator
echo "Starting Convexa Orchestrator..."
# Render will pass environment variables automatically
python3 orchestrator.py --token ETH --duration 5rounds
