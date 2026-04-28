# Convexa Testnet Deployment Checklist

## Step 14 Completion Status
✓ Interface audit completed  
✓ CLI argument parsing implemented  
✓ DryRunAdapter fully functional  
✓ AXL node management implemented  
✓ Stake collection window implemented  
✓ Single-round execution (execute_single_round) implemented  
✓ Terminal display with conviction meters implemented  
✓ Orchestrator-level final settlement implemented  
✓ 5-round dry-run completed with audit trail validation  
✓ 10-round dry-run completed with complete audit trail  
✓ All audit tables (round_trace, keeperhub_jobs, swap_quotes, swap_executions, safety_events, strategy_adaptations, axl_message_audit) validated  

## Pre-Testnet Requirements

### 1. Environment Configuration
- [ ] Create `.env.testnet` file with testnet RPC endpoints
  - Sepolia/Goerli Alchemy RPC for eth_chainId probes
  - Uniswap V3 subgraph endpoint
  - KeeperHub testnet address and network ID
- [ ] Set `DRY_RUN=false` in environment
- [ ] Update `USE_KEEPERHUB=true` for real job submission
- [ ] Provide testnet contract addresses:
  - `DEBATE_ESCROW_ADDRESS`: deployed DebateEscrow.sol contract
  - `CONVICTION_TRACKER_ADDRESS`: deployed ConvictionTracker.sol contract

### 2. Wallet & Funding
- [ ] Testnet wallet with sufficient ETH for:
  - Stake deposits (test with minimum 0.001 ETH per side)
  - Gas for conviction updates, swaps, and settlements
  - KeeperHub job submission fees
- [ ] Test wallets: bull_address, bear_address, judge_address (from config)

### 3. AXL Node Setup
- [ ] Verify AXL node binaries available in `axl-nodes/`
- [ ] Confirm peer IDs match risk_manager validation expectations
- [ ] Test AXL health endpoints before debate launch

### 4. Contract Deployment
- [ ] Deploy DebateEscrow.sol to testnet
- [ ] Deploy ConvictionTracker.sol to testnet
- [ ] Verify contract ABIs match in `contracts/abi/`
- [ ] Update orchestrator with deployed addresses

### 5. Data Sources
- [ ] Confirm Uniswap V3 pool exists for ETH/USDC on testnet
- [ ] Verify market_data.py can fetch real quotes (or use fallback)
- [ ] Test KeeperHub integration if available on testnet

### 6. Database & Audit Trail
- [ ] Use testnet-specific SQLite path (or centralized DB)
- [ ] Ensure schema migrations applied
- [ ] Verify audit table creation before first debate

## Testnet Launch Command

```bash
# Activate virtualenv
source ./.venv/bin/activate

# Load testnet environment
export $(cat .env.testnet | xargs)

# Run orchestrator (no --dry-run flag)
python agents/orchestrator.py --token ETH --duration 3rounds --round-interval 30 --min-stake 0.001
```

## Expected Testnet Behavior

- 3-round debate with 30-second intervals (configurable)
- Stake collection window: 2 minutes
- Real AXL message exchange (with peer_id validation)
- Real Uniswap quotes fetched; fallback to deterministic pricing if unavailable
- KeeperHub job submission for each round + final settlement
- ConvictionTracker updates posted onchain
- DebateEscrow settlement called at end
- Complete audit trail written to SQLite for analytics

## Validation on Testnet

After launch, verify:
1. **Terminal Output**: Watch conviction meter update each round, confirm no [DRY_RUN] labels
2. **AXL Messages**: Confirm both bull and bear arguments published and received (may show validation warnings if peers differ from AXL config)
3. **Uniswap Quotes**: Check swap_quotes table for real prices; verify microswaps execute
4. **KeeperHub Jobs**: Query keeperhub_jobs for job_id and tx_hash confirmations
5. **Settlement**: Final settlement shows winner/draw and balance deltas (will be 0 in draw)
6. **Database**: Run final audit query:
   ```sql
   SELECT COUNT(*) FROM round_trace WHERE session_id = 'YOUR_SESSION_ID';
   -- Should return 3 (for 3 rounds)
   ```

## Rollback & Debugging

- If AXL signature validation fails: check peer_id mismatch warnings (normal in testnet)
- If Uniswap quote fails: check pool address in market_data.py for correct testnet pool
- If KeeperHub times out: verify network connectivity and job submission permissions
- If settlement fails: confirm DebateEscrow contract has sufficient escrow balance

## Next Steps (Post-Testnet)

1. **Demo Recording**: Run 2-3 debate rounds with real stakes (small amounts) and record
2. **Mainnet Prep**: Update contract addresses and RPC endpoints to mainnet
3. **Security Audit**: Review risk_manager.py, dry_run_adapter.py for production readiness
4. **Monitoring**: Set up alerting for debate_timeout and gas_spike events

---
**Last Updated**: 2026-04-28  
**Status**: Ready for testnet deployment
