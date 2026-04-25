#!/bin/bash
echo "🎭 Setting up Debate Market..."

# Check prerequisites
node -v || { echo "❌ Node.js not found. Install Node 18+"; exit 1; }
python3 -V || { echo "❌ Python not found. Install Python 3.10+"; exit 1; }

# Python env
echo "📦 Installing Python dependencies..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -q

# Node dependencies
echo "📦 Installing Node dependencies..."
npm install
cd frontend && npm install && cd ..

# Hardhat
echo "🔨 Compiling contracts..."
cd contracts && printf 'n\n' | HARDHAT_DISABLE_TELEMETRY_PROMPT=1 npx hardhat compile && cd ..

# Env setup
if [ ! -f .env ]; then
  cp .env.example .env
  echo "⚠️  .env created from template — fill in your API keys before running!"
fi

# DB directory
mkdir -p utils/db data/logs

echo "✅ Setup complete! Fill in .env then run: python agents/orchestrator.py"