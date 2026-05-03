# Step 19.7 Clean Validation Environment Preparation Guide

**Purpose:** Prepare a completely fresh environment to demonstrate the system works from a cold start without relying on any accumulated development state.

## Prerequisites

Before starting this guide, ensure you have:
- [ ] Unichain Sepolia testnet faucet access (uniin.io/faucet)
- [ ] A wallet seed phrase for generating fresh wallets
- [ ] Git repository with all security fixes committed
- [ ] Screen recording software installed (SimpleScreenRecorder, OBS, ScreenFlow, etc.)
- [ ] Terminal multiplexer available (screen or tmux)

## Step 1: Generate Fresh Wallets

Create three new Ethereum wallets using a wallet generator (MetaMask, ethers.js, or hardhat):

```bash
# Using hardhat:
cd /Users/swanandibhende/Documents/Projects/convexa/contracts
npx hardhat accounts --network unichainSepolia

# Or using web3.py:
cd /Users/swanandibhende/Documents/Projects/convexa
source .venv/bin/activate
python -c "
from eth_account import Account
from web3 import Web3

# Generate 3 fresh wallets
for i in range(3):
    account = Account.create()
    print(f'Wallet {i+1}:')
    print(f'  Address: {account.address}')
    print(f'  Private Key: {account.key.hex()}')
    print()
"
```

Generate addresses for:
1. **Deployer Wallet** - Deploys contracts, signs owner functions
2. **Agent/Judge Wallet** - Signs judge agent functions, generates verdicts
3. **Staker Wallet** - Stakes ETH on one side during debate
4. **KeeperHub Executor Wallet** - Calls settlement (use existing KEEPERHUB_EXECUTOR_ADDRESS)

**Record these securely OUTSIDE the git repository.**

## Step 2: Fund Wallets from Unichain Sepolia Faucet

Each wallet needs testnet ETH for:
- Deployer: ~0.5 ETH (for contract deployment gas)
- Agent: ~0.5 ETH (for orchestrator.py operations)
- Staker: ~1.0 ETH (for debate stakes and testing)
- Executor: Already funded (existing service address)

Visit: https://sepolia.drip.unichaindb.com/

Add each address and request 2.0 ETH per address.

Verify funding:

```bash
cd /Users/swanandibhende/Documents/Projects/convexa
source .venv/bin/activate
python -c "
from web3 import Web3
import os

web3 = Web3(Web3.HTTPProvider(os.getenv('ALCHEMY_RPC_URL')))

addresses = [
    '0x...DEPLOYER_ADDRESS...',
    '0x...AGENT_ADDRESS...',
    '0x...STAKER_ADDRESS...',
]

for addr in addresses:
    balance = web3.eth.get_balance(addr)
    print(f'{addr}: {web3.from_wei(balance, \"ether\")} ETH')
"
```

## Step 3: Update .env with Fresh Wallet Addresses

**DO NOT commit this .env to git!**

```bash
cd /Users/swanandibhende/Documents/Projects/convexa

# Edit .env and update:
DEPLOYER_PRIVATE_KEY=0x[NEW_DEPLOYER_PRIVATE_KEY]
AGENT_WALLET_PRIVATE_KEY=0x[NEW_AGENT_PRIVATE_KEY]
AGENT_WALLET_ADDRESS=0x[NEW_AGENT_ADDRESS]
BULL_STAKER_PRIVATE_KEY=0x[NEW_STAKER_PRIVATE_KEY]
BULL_STAKER_ADDRESS=0x[NEW_STAKER_ADDRESS]

# Keep existing KeeperHub executor
KEEPERHUB_EXECUTOR_ADDRESS=0xB2D43D16C434f44ad6DF632b5A0eD4e04256e3eD
```

## Step 4: Clear SQLite Databases

Remove all accumulated state:

```bash
cd /Users/swanandibhende/Documents/Projects/convexa

# List SQLite databases
find . -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" | grep -v ".venv\|node_modules"

# Delete them (or rename with .bak extension)
rm -f data/audit.db
rm -f data/orchestrator.db
rm -f data/judge.db
rm -f data/bull.db
rm -f data/bear.db

# Verify they're gone
ls -la data/
```

## Step 5: Clear and Restart AXL Nodes

**Stop all running AXL processes:**

```bash
cd /Users/swanandibhende/Documents/Projects/convexa/axl-nodes

# Stop existing nodes
./stop-all.sh

# Verify they're stopped
ps aux | grep axl | grep -v grep
# Should return nothing

# Wait 5 seconds
sleep 5
```

**Delete all AXL node data directories:**

```bash
cd /Users/swanandibhende/Documents/Projects/convexa/axl-nodes

# Clear all node state
rm -rf bear/data/*
rm -rf bull/data/*
rm -rf judge/data/*

# Remove old PID files
rm -f logs/*.pid

# Verify they're clean
find . -name "*.db" -o -name "*.yaml" | grep data/
# Should return nothing
```

**Start fresh AXL nodes:**

```bash
# In a screen/tmux session:
cd /Users/swanandibhende/Documents/Projects/convexa/axl-nodes

# In separate terminals or screen windows:
# Terminal 1 - Bear Node
./start-all.sh bear

# Terminal 2 - Bull Node
./start-all.sh bull

# Terminal 3 - Judge Node
./start-all.sh judge

# Verify nodes started and generated new peer IDs
sleep 10
cat logs/bear.log | grep "peer_id\|listening"
cat logs/bull.log | grep "peer_id\|listening"
cat logs/judge.log | grep "peer_id\|listening"
```

## Step 6: Clear Hardhat Artifacts and Cache

```bash
cd /Users/swanandibhende/Documents/Projects/convexa/contracts

# Delete compiled artifacts
rm -rf artifacts/
rm -rf cache/
rm -rf ignition/deployments/

# Force recompile
npx hardhat compile
```

## Step 7: Verify Clean Environment

Create a verification checklist:

```bash
#!/bin/bash
set -e

cd /Users/swanandibhende/Documents/Projects/convexa

echo "=== Clean Environment Verification ==="
echo ""

echo "✓ Checking .env is configured with fresh wallets:"
grep "DEPLOYER_PRIVATE_KEY\|AGENT_WALLET" .env | head -2

echo ""
echo "✓ Checking SQLite databases are clean:"
find data -name "*.db" 2>/dev/null || echo "  No databases found (clean)"

echo ""
echo "✓ Checking AXL node data directories are clean:"
for dir in axl-nodes/{bear,bull,judge}/data; do
    [ -d "$dir" ] && [ -z "$(ls -A $dir)" ] && echo "  $dir is empty (clean)" || echo "  $dir may contain data"
done

echo ""
echo "✓ Checking Hardhat artifacts are clean:"
[ ! -d "contracts/artifacts" ] && echo "  artifacts/ deleted (clean)" || echo "  artifacts/ exists"
[ ! -d "contracts/cache" ] && echo "  cache/ deleted (clean)" || echo "  cache/ exists"

echo ""
echo "✓ Verifying AXL nodes are running:"
curl -s http://localhost:8001/status 2>/dev/null && echo "  Bear node responding" || echo "  Bear node not responding"
curl -s http://localhost:8002/status 2>/dev/null && echo "  Bull node responding" || echo "  Bull node not responding"
curl -s http://localhost:8003/status 2>/dev/null && echo "  Judge node responding" || echo "  Judge node not responding"

echo ""
echo "✓ Environment ready for fresh validation run!"
```

## Step 8: Pre-Recording Setup

Before starting the actual validation run:

1. **Arrange Windows:**
   - Top-left: Orchestrator terminal (main process)
   - Top-right: AXL node logs (combined output)
   - Bottom-left: Browser with Unichain explorer
   - Bottom-right: Browser with KeeperHub dashboard
   - Secondary monitor: Frontend dashboard (optional)

2. **Start Screen Recording:**
   ```bash
   # Using SimpleScreenRecorder or OBS:
   - Select full screen or custom region
   - Set 1080p resolution, 30 FPS
   - Start recording BEFORE running orchestrator
   - File: final-validation-recording-$(date +%s).mp4
   ```

3. **Prepare Terminal Windows:**
   ```bash
   # Terminal 1: Orchestrator
   cd /Users/swanandibhende/Documents/Projects/convexa
   source .venv/bin/activate
   
   # Terminal 2: AXL logs
   cd /Users/swanandibhende/Documents/Projects/convexa/axl-nodes
   tail -f logs/bear.log logs/bull.log logs/judge.log
   
   # Terminal 3: Explorer monitoring
   open https://sepolia.uniscan.xyz/
   # Filter to AGENT_WALLET_ADDRESS
   
   # Terminal 4: KeeperHub dashboard
   open https://app.keeperhub.com/
   # Log in and open jobs dashboard
   ```

## Step 9: Execute Final Validation Run

From the main orchestrator terminal:

```bash
cd /Users/swanandibhende/Documents/Projects/convexa
source .venv/bin/activate

# Capture start timestamp
VALIDATION_START=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "Validation Start: $VALIDATION_START"

# Run orchestrator for 10 rounds (or until conviction threshold is reached)
python agents/orchestrator.py \
    --token ETH \
    --duration 10rounds \
    --verbose

# Capture end timestamp
VALIDATION_END=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "Validation End: $VALIDATION_END"
```

**DO NOT STOP RECORDING until:**
- All debate rounds complete OR
- Conviction threshold (70) is reached OR
- Settlement is confirmed on-chain

## Step 10: Post-Validation Documentation

After the run completes, immediately document:

```bash
# Capture session ID from orchestrator output
SESSION_ID="[SESSION_ID_FROM_OUTPUT]"

# Record contract addresses used
DEBATE_ESCROW="[ADDRESS_FROM_DEPLOYMENT]"
CONVICTION_TRACKER="[ADDRESS_FROM_DEPLOYMENT]"

# Document all transaction hashes
# From explorer: https://sepolia.uniscan.xyz/

# Verify SQLite audit trail
sqlite3 data/audit.db ".tables"
sqlite3 data/audit.db "SELECT COUNT(*) FROM debate_sessions WHERE session_id = '$SESSION_ID';"
sqlite3 data/audit.db "SELECT COUNT(*) FROM round_trace WHERE session_id = '$SESSION_ID';"
sqlite3 data/audit.db "SELECT COUNT(*) FROM axl_message_audit WHERE session_id = '$SESSION_ID';"
sqlite3 data/audit.db "SELECT COUNT(*) FROM keeperhub_jobs WHERE session_id = '$SESSION_ID';"

# Verify all three partner tracks
echo "=== Verification Checklist ==="
echo "AXL Messages:"
sqlite3 data/audit.db "SELECT COUNT(*) FROM axl_message_audit WHERE accepted = 1;" 
echo "  Expected: >= 3 (at least 1 per round)"

echo "Uniswap Swaps:"
echo "  Open https://sepolia.uniscan.xyz/ and verify swap transactions"
echo "  Expected: >= 3 confirmed swaps"

echo "KeeperHub Jobs:"
echo "  Open https://app.keeperhub.com/ and verify completed jobs"
echo "  Expected: >= 3 confirmed jobs"
```

## Troubleshooting Clean Environment Issues

### Problem: AXL nodes fail to start
**Solution:**
```bash
# Check ports are free
lsof -i :8001 :8002 :8003

# Kill any existing processes
kill -9 $(lsof -t -i :8001)

# Check logs for errors
tail -100 axl-nodes/logs/*.log
```

### Problem: Database locks or corruption
**Solution:**
```bash
# Remove all .lock files
find . -name "*.lock" -delete

# Reset database to empty
rm -f data/*.db
rm -f data/audit.db
```

### Problem: Contracts won't deploy
**Solution:**
```bash
# Verify RPC connectivity
python -c "
from web3 import Web3
import os
web3 = Web3(Web3.HTTPProvider(os.getenv('ALCHEMY_RPC_URL')))
print(f'Connected: {web3.is_connected()}')
print(f'Chain ID: {web3.eth.chain_id}')
"

# Verify deployer wallet has ETH
python -c "
from web3 import Web3
from eth_account import Account
import os
deployer = Account.from_key(os.getenv('DEPLOYER_PRIVATE_KEY'))
web3 = Web3(Web3.HTTPProvider(os.getenv('ALCHEMY_RPC_URL')))
balance = web3.eth.get_balance(deployer.address)
print(f'{deployer.address}: {web3.from_wei(balance, \"ether\")} ETH')
"
```

## Final Checklist

Before hitting "record":

- [ ] Fresh wallets generated and documented
- [ ] All wallets funded with testnet ETH
- [ ] .env updated with fresh addresses
- [ ] SQLite databases cleared
- [ ] AXL nodes stopped and data cleared
- [ ] AXL nodes restarted with new peer IDs
- [ ] Hardhat artifacts cleared
- [ ] Screen recording software ready
- [ ] All browser windows positioned
- [ ] Terminal multiplexer configured
- [ ] Network connectivity verified
- [ ] Git changes committed (don't include .env)
- [ ] README updated if needed

**Status:** Ready for validation run ✓
