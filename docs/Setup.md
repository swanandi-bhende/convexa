# Setup Guide

## Prerequisites

- **Node.js:** 18+ ([download](https://nodejs.org/))
- **Python:** 3.10+ ([download](https://www.python.org/))
- **AXL binary:** Place at `axl-nodes/axl` (included in repo)

## Installation (First Time)

### 1. Clone and Install Dependencies

```bash
git clone <repo-url> convexa && cd convexa
./setup.sh
```

This script:
- Creates a Python virtual environment and installs dependencies
- Installs Node.js packages for frontend and contracts
- Compiles Hardhat contracts
- Creates `data/logs` and `utils/db` directories
- Generates `.env` from `.env.example`

### 2. Configure Environment Variables

Edit `.env` with your API keys:

```bash
# LLM (Groq — free tier available)
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile

# Blockchain RPC (Alchemy — free tier available)
ALCHEMY_RPC_URL=https://unichain-sepolia.g.alchemy.com/v2/your_key
ALCHEMY_WS_URL=wss://unichain-sepolia.g.alchemy.com/v2/your_key

# Wallets (use testnet wallets)
DEPLOYER_PRIVATE_KEY=your_deployer_private_key
AGENT_WALLET_PRIVATE_KEY=your_agent_wallet_key
AGENT_WALLET_ADDRESS=your_agent_wallet_address

# KeeperHub
KEEPERHUB_API_KEY=your_keeperhub_api_key
KEEPERHUB_EXECUTOR_ADDRESS=keeperhub_executor_wallet
KEEPERHUB_MCP_URL=https://mcp.keeperhub.com

# Uniswap
UNISWAP_API_KEY=your_uniswap_api_key
UNISWAP_API_BASE=https://api.uniswap.org/v1
MARKET_DATA_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/your_key
THEGRAPH_UNISWAP_V3_ENDPOINT=https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3
UNISWAP_V3_POOL_ETH_USDC=your_pool_address
```

### 3. Activate Python Environment

```bash
source venv/bin/activate
```

On Windows:
```bash
venv\Scripts\activate
```

### 4. Verify Setup

```bash
python orchestrator.py --help
```

Should display orchestrator help without errors.

## Quick Test

Run a dry-run debate (no onchain transactions):

```bash
python orchestrator.py --token ETH --duration 5rounds --dry-run
```

This spins up local AXL nodes, runs a debate, and shuts down cleanly.

## Key Directories

| Directory | Purpose |
| --- | --- |
| `agents/` | Bull, bear, judge agent implementations |
| `contracts/` | Solidity contracts, deployment config |
| `keeper/` | KeeperHub integration |
| `uniswap/` | Uniswap API integration, swap execution |
| `utils/` | Shared utilities, database, market data |
| `data/logs` | Runtime logs |
| `utils/db` | SQLite database (created at runtime) |

## Troubleshooting

**Issue:** Setup script fails on `npx hardhat compile`  
→ Run `cd contracts && npm install && cd ..` then retry

**Issue:** `GROQ_API_KEY` error  
→ Get free key from [console.groq.com](https://console.groq.com)

**Issue:** Wallet balance insufficient  
→ Use Unichain Sepolia faucet for testnet ETH

**Issue:** AXL binary not found  
→ Verify `axl-nodes/axl` exists and is executable: `chmod +x axl-nodes/axl`

See [Troubleshooting.md](Troubleshooting.md) for more solutions.
