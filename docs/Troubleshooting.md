# Troubleshooting

Common issues and solutions for Convexa setup and operation.

## Setup Issues

### Issue: `python3: command not found`

**Problem:** Python not installed or not in PATH  
**Solution:**
1. Install Python 3.10+ from [python.org](https://www.python.org/)
2. Verify installation:
   ```bash
   python3 --version
   ```
3. If still not found, add Python to PATH (macOS/Linux):
   ```bash
   export PATH="/usr/local/bin:$PATH"
   ```

---

### Issue: `node: command not found`

**Problem:** Node.js not installed  
**Solution:**
1. Install Node.js 18+ from [nodejs.org](https://nodejs.org/)
2. Verify installation:
   ```bash
   node --version
   npm --version
   ```

---

### Issue: `venv/bin/activate: No such file or directory`

**Problem:** Virtual environment not created  
**Solution:**
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows
```

---

### Issue: `pip install -r requirements.txt` fails

**Problem:** Dependency installation error  
**Solution:**
1. Ensure virtual environment is activated:
   ```bash
   source venv/bin/activate
   ```
2. Upgrade pip:
   ```bash
   pip install --upgrade pip
   ```
3. Install with verbose output to see error:
   ```bash
   pip install -r requirements.txt -v
   ```
4. If specific package fails, install separately:
   ```bash
   pip install package-name==version
   ```

---

### Issue: `npx hardhat compile` fails

**Problem:** Hardhat compilation error  
**Solution:**
1. Ensure in `contracts/` directory:
   ```bash
   cd contracts
   ```
2. Install Hardhat dependencies:
   ```bash
   npm install
   ```
3. Clear cache and retry:
   ```bash
   rm -rf artifacts/ cache/
   npx hardhat compile
   ```

---

## Configuration Issues

### Issue: `.env` file not created or incomplete

**Problem:** Missing environment variables  
**Solution:**
1. Copy template:
   ```bash
   cp .env.example .env
   ```
2. Fill in API keys:
   ```bash
   # Open .env and add:
   GROQ_API_KEY=your_groq_key
   ALCHEMY_RPC_URL=your_alchemy_url
   AGENT_WALLET_PRIVATE_KEY=your_private_key
   # ... (all other keys)
   ```
3. Verify all keys present:
   ```bash
   grep -c "your_" .env  # Should be 0
   ```

---

### Issue: `GROQ_API_KEY` error

**Problem:** No Groq API key or invalid key  
**Solution:**
1. Get free key from [console.groq.com](https://console.groq.com)
2. Sign in, generate API key
3. Add to `.env`:
   ```
   GROQ_API_KEY=gsk_xxxxx...
   ```
4. Verify by running:
   ```bash
   python -c "import os; print(os.getenv('GROQ_API_KEY'))"
   ```

---

### Issue: `ALCHEMY_RPC_URL` error

**Problem:** Invalid RPC URL or network not enabled  
**Solution:**
1. Get free Alchemy key from [alchemy.com](https://www.alchemy.com/)
2. Create Unichain Sepolia app
3. Verify URL format:
   ```
   https://unichain-sepolia.g.alchemy.com/v2/YOUR_KEY
   ```
4. Test RPC:
   ```bash
   curl -X POST ALCHEMY_RPC_URL \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}'
   ```
   Should return `"result":"0x4e0d0"` (Unichain Sepolia chain ID)

---

## Runtime Issues

### Issue: Demo hangs or exits early

**Problem:** Process stuck or crashed  
**Solution:**
1. Run dry-run first (no network):
   ```bash
   python orchestrator.py --token ETH --duration 5rounds --dry-run
   ```
2. Check logs:
   ```bash
   tail -f data/logs/orchestrator.log
   ```
3. Kill stuck process:
   ```bash
   pkill -f orchestrator.py
   pkill -f "axl -config"
   ```
4. Retry with verbose output:
   ```bash
   python orchestrator.py --token ETH --duration 2rounds --verbose
   ```

---

### Issue: AXL nodes fail to start

**Problem:** "axl: command not found" or "Permission denied"  
**Solution:**
1. Verify binary exists:
   ```bash
   ls -la axl-nodes/axl
   ```
2. Make executable:
   ```bash
   chmod +x axl-nodes/axl
   ```
3. Test directly:
   ```bash
   ./axl-nodes/axl -help
   ```
4. Check logs:
   ```bash
   tail -f data/logs/axl_bull.log
   tail -f data/logs/axl_bear.log
   tail -f data/logs/axl_judge.log
   ```

---

### Issue: Agent communication timeout

**Problem:** Judge waits forever for bull/bear arguments  
**Solution:**
1. Check AXL node health:
   ```bash
   curl http://127.0.0.1:8001/health
   curl http://127.0.0.1:8002/health
   curl http://127.0.0.1:8003/health
   ```
   All should return `{"status": "healthy"}`

2. Check AXL logs for errors:
   ```bash
   grep "ERROR\|error" data/logs/axl_*.log
   ```

3. Restart AXL nodes:
   ```bash
   pkill -f "axl -config"
   sleep 2
   python orchestrator.py --token ETH --duration 2rounds --verbose
   ```

---

### Issue: "Insufficient balance" error

**Problem:** Wallet doesn't have enough ETH for transaction  
**Solution:**
1. Check wallet balance:
   ```bash
   # Use block explorer or:
   curl -X POST ALCHEMY_RPC_URL \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc":"2.0",
       "method":"eth_getBalance",
       "params":["YOUR_ADDRESS","latest"],
       "id":1
     }'
   ```

2. Fund wallet from faucet:
   ```bash
   # Unichain Sepolia faucet
   curl -X POST https://unichain-sepolia-faucet.onrender.com/ \
     -H "Content-Type: application/json" \
     -d '{"address":"YOUR_ADDRESS"}'
   ```

3. Wait for confirmation (may take 30-60s)

---

### Issue: Settlement transaction fails

**Problem:** "KeeperHub API error" or transaction reverted  
**Solution:**
1. Verify KeeperHub credentials:
   ```bash
   grep KEEPERHUB .env | grep -v "#"
   ```

2. Check executor wallet has balance:
   ```bash
   # Fetch executor wallet balance (see above)
   ```

3. Check transaction logs:
   ```bash
   sqlite3 utils/db/settlements.db "SELECT * FROM settlements ORDER BY timestamp DESC LIMIT 5;"
   ```

4. For persistent issues, run in dry-run mode:
   ```bash
   python orchestrator.py --token ETH --duration 2rounds --dry-run
   ```

---

## Database Issues

### Issue: SQLite database locked

**Problem:** "database is locked" error  
**Solution:**
1. Ensure only one process accessing database:
   ```bash
   pkill -f orchestrator.py
   sleep 2
   ```

2. Check for stale connections:
   ```bash
   lsof | grep settlements.db
   ```

3. Remove lock file if stuck:
   ```bash
   rm -f utils/db/settlements.db-wal
   rm -f utils/db/settlements.db-shm
   ```

4. Retry operation

---

### Issue: Database corruption

**Problem:** "database disk image is malformed"  
**Solution:**
1. Backup database:
   ```bash
   cp utils/db/settlements.db utils/db/settlements.db.backup
   ```

2. Rebuild database:
   ```bash
   rm utils/db/settlements.db
   python orchestrator.py --init-db  # Creates fresh schema
   ```

3. If data recovery needed, restore from backup:
   ```bash
   cp utils/db/settlements.db.backup utils/db/settlements.db
   ```

---

## Contract Issues

### Issue: "Contract not found" error

**Problem:** Contract not deployed at expected address  
**Solution:**
1. Verify contract deployed:
   ```bash
   # Check .env for contract addresses
   grep CONTRACT_ADDRESS .env
   ```

2. Check block explorer:
   - DebateEscrow: `https://unichain-sepolia.blockscout.com/address/0x9034105e9C469Be8f8A6ea3115C39F9D8dd45e7b`
   - ConvictionTracker: `https://unichain-sepolia.blockscout.com/address/0x01Dd5eB506d1B760e0EB8962628186be44B152Fe`

3. Redeploy if needed:
   ```bash
   cd contracts
   npx hardhat ignition deploy ./ignition/modules/DebateEscrow.ts --network unichainSepolia
   ```

---

### Issue: Contract call reverts

**Problem:** Transaction fails with "execution reverted"  
**Solution:**
1. Check contract logs:
   ```bash
   grep "revert\|Revert" data/logs/*.log
   ```

2. Common revert reasons:
   - Access control: Caller not authorized
   - State: Debate not active or already settled
   - Input: Invalid conviction score (-100 to +100 required)

3. Verify pre-conditions:
   ```bash
   # Check debate is active
   # Check conviction is in valid range
   # Check caller has correct role
   ```

---

## Performance Issues

### Issue: Debate takes too long (>30 seconds per round)

**Problem:** Slow agent reasoning or network latency  
**Solution:**
1. Check agent response times:
   ```bash
   grep "Agent response time" data/logs/*.log
   ```

2. Profile slow operations:
   ```bash
   python orchestrator.py --token ETH --duration 2rounds --profile
   ```

3. Consider:
   - Network latency to Groq API (switch region if possible)
   - RPC endpoint latency (try different Alchemy region)
   - Local machine load (close other applications)

---

### Issue: Memory usage increasing (memory leak)

**Problem:** Process consumes more memory over time  
**Solution:**
1. Monitor memory:
   ```bash
   ps aux | grep orchestrator.py
   # Watch RSS column
   ```

2. Check for large collections not being cleared:
   ```bash
   grep -n "cache\|buffer\|queue" agents/*.py | grep -v "clear\|reset"
   ```

3. Run garbage collection explicitly:
   ```python
   import gc
   gc.collect()
   ```

4. Restart process periodically for long-running demos

---

## Getting Help

If issues persist:

1. **Check logs:**
   ```bash
   tail -100 data/logs/*.log
   ```

2. **Run diagnostic script:**
   ```bash
   python scripts/diagnose.py
   ```

3. **Review:** [Setup.md](Setup.md), [Demo.md](Demo.md), [Tests.md](Tests.md)

4. **Report issue** with:
   - Error message and stack trace
   - Output of `diagnostics.py`
   - `.env` file (without secrets)
   - OS and Python version
